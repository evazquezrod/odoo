import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { TranslateWebpageOption } from "./translate_webpage_option";
import { rpc } from "@web/core/network/rpc";
import { BuilderAction } from "@html_builder/core/builder_action";
import { reactive } from "@odoo/owl";

export class CustomizeTranslationTabPlugin extends Plugin {
    static id = "customizeTranslationTab";
    static shared = ["getTranslationState"];
    resources = {
        builder_actions: {
            TranslateWebpageAI,
        },
        translate_options: [
            withSequence(
                1,
                this.getTranslationOptionBlock("translate-webpage", _t("Translation"), {
                    OptionComponent: TranslateWebpageOption,
                    props: {
                        getTranslationState: () => this.translationState,
                    }
                })
            ),
        ],
    }

    setup() {
        this.translationState = reactive({
            isLoading: undefined,
            isSuccess: undefined,
        });
    }

    getTranslationState() {
        return this.translationState;
    }

    getTranslationOptionBlock(id, name, options) {
        options.selector = "*";
        return {
            id: id,
            snippetModel: {},
            element: this.document.body,
            options: [options],
            isRemovable: false,
            isClonable: false,
            containerTopButtons: [],
        };
    }
}

class TranslateWebpageAI extends BuilderAction {
    static id = "translateWebpageAI";
    static dependencies = ["customizeTranslationTab"];

    async apply({ editingElement: bodyEl }) {
        const translationState = this.dependencies.customizeTranslationTab.getTranslationState();
        translationState.isLoading = true;
        const language = this.services.website.currentWebsite.metadata.lang;
        const elements = this.getTranslatableElements(bodyEl);
        const translationTasks = this.buildTranslationTasks(elements, language);

        const responses = await this.runTranslationTasks(translationTasks, language);
        const isSuccess = this.applyTranslatedResults(translationTasks, responses);
        translationState.isLoading = false;
        if (!isSuccess) {
            this.showNotification("Translation aborted due to a failure in processing.", "Translation Error", "danger");
        }
    }

    getTranslatableElements(container) {
        return Array.from(container.querySelectorAll("[data-oe-translation-state='to_translate']"));
    }

    /**
     * Determines if text should be skipped during translation processing.
     * @param {string} text - Input text to check
     * @returns {boolean} True if text should be skipped
     * @example
     * Two cases are skipped:
     * 1. Empty or whitespace-only strings:
     *    - "" (empty string)
     *    - "   " (whitespace only)
     *    - "\n\t " (line breaks/tabs)
     *
     * 2. Strings containing ONLY separator characters:
     *    - | (vertical bar)
     *    - · (middle dot)
     *    - - (hyphen), – (en dash), — (em dash)
     *    - • (bullet point)
     *    - Any combination of these (e.g., "|---•·")
     *
     * Examples of skipped text:
     *    "|", "---", "·–•", "——", "     "
     *
     * Examples of processed text:
     *    "Hello", "A-B", "• Item", "123", "• Text •"
     */
    isSkippableText(text) {
        const trimmed = text.trim();
        return trimmed === "" || /^[|·\-–—•]+$/.test(trimmed);
    }

    buildTranslationTasks(elements, language) {
        const tasks = [];
        let id = 1;
        for (const el of elements) {
            const text = el.textContent.replace(/[\u200B-\u200D\uFEFF]/g, "").trim();
            if (!text || this.isSkippableText(text)) continue;
            tasks.push({ el, id: id++, text });
        }
        return tasks;
    }

    /**
     * Executes translation tasks in chunks
     * @param {Object[]} tasks - Translation tasks
     * @param {string} language - Target language
     * @returns {Promise<string[]>} Array of translation responses
     * @example
     * // Sends texts to translation API and returns responses
     * runTranslationTasks(tasks, 'fr');
     */
    async runTranslationTasks(tasks, language) {
        const chunks = this.chunkTranslationTasksByLength(tasks, 2000);
        const allResults = [];

        const systemMessage = {
            role: "system",
            content:
                "You are a translation assistant. Your goal is to translate multiple blocks of text.\n" +
                "Instructions:\n" +
                "- Each block is wrapped with <generatedtext id=\"X\">...</generatedtext>\n" +
                "- Return all blocks translated using the same format.\n" +
                "- Do not add HTML or comments.",
        };

        for (const chunk of chunks) {
            const prompt = chunk.map(t => `<generatedtext id="${t.id}">${t.text}</generatedtext>`).join("\n");
            const conversation = [
                systemMessage,
                { role: "user", content: `Translate the following to ${language}:\n\n${prompt}` },
            ];
            const response = await rpc("/web_editor/generate_text", {
                prompt,
                conversation_history: conversation,
            }, { shadow: true });
            allResults.push(response);
        }
        return allResults;
    }

    /**
     * Breaks translation tasks into smaller groups (chunks) so that each group
     * stays within a safe size limit.
     *
     * Why? Translation services like GPT have limits on how much text you can
     * send in one request. If we send too much at once, it may fail or get cut off.
     * So, we group tasks together in smaller batches that stay under that limit.
     *
     * Each task is turned into a line like this:
     * <generatedtext id="123">Your text here</generatedtext>
     *
     * This function keeps track of how long each batch would be, and once the
     * batch is getting too big, it starts a new one.
     *
     * @param {Array} tasks - A list of things we want to translate (each has an `id` and `text`)
     * @param {number} limit - The maximum allowed length of text per batch
     * @returns {Array} A list of batches, where each batch is a list of tasks
     */
    chunkTranslationTasksByLength(tasks, limit) {
        const chunks = [];
        let currentChunk = [];
        let currentLength = 0;
        for (const task of tasks) {
            const promptLine = `<generatedtext id="${task.id}">${task.text}</generatedtext>\n`;
            if (currentLength + promptLine.length > limit) {
                chunks.push(currentChunk);
                currentChunk = [];
                currentLength = 0;
            }
            currentChunk.push(task);
            currentLength += promptLine.length;
        }
        if (currentChunk.length) {
            chunks.push(currentChunk);
        }
        return chunks;
    }

    applyTranslatedResults(tasks, responses) {
        const map = new Map(tasks.map(t => [t.id.toString(), t.el]));
        const regex = /<generatedtext id="(\d+)">([\s\S]*?)<\/generatedtext>/g;

        for (const response of responses) {
            let match;
            while ((match = regex.exec(response)) !== null) {
                const [, id, translated] = match;
                const el = map.get(id);
                if (el && translated.trim()) {
                    this.applyTextNodeTranslation(el, translated.trim());
                } else {
                    this.showNotification(`Translation failed for ID ${id}`, "Translation Error", "danger");
                    return false;
                }
            }
        }
        return true;
    }

    applyTextNodeTranslation(el, translatedText) {
        const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null, false);
        const textNodes = [];
        while (walker.nextNode()) {
            const node = walker.currentNode;
            if (node.textContent.trim()) {
                textNodes.push(node);
            }
        }
        if (textNodes.length === 0) return;
        textNodes[0].textContent = translatedText;
        for (let i = 1; i < textNodes.length; i++) {
            textNodes[i].textContent = "";
        }
    }

    showNotification(message, title, type, context) {
        context.services.notification.add(message, {
            title: _t(title),
            type,
            sticky: true,
        });
    }
}

registry.category("translation-plugins").add(CustomizeTranslationTabPlugin.id, CustomizeTranslationTabPlugin);
