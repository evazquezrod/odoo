import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { nextLeaf } from "@html_editor/utils/dom_info";
import { isBlock } from "@html_editor/utils/blocks";
import { closestElement } from "@html_editor/utils/dom_traversal";
// import { unwrapContents } from "@html_editor/utils/dom";
import {
    EmbeddedFileDocumentsSelector,
    renderEmbeddedFileBox,
} from "./embedded_file_documents_selector";

export class EmbeddedFilePlugin extends Plugin {
    static id = "embeddedFile";
    static dependencies = ["dom", "history", "embeddedComponents", "selection"];
    static defaultConfig = {
        allowFile: true,
    };

    // Extends the base class resources
    resources = {
        user_commands: {
            id: "uploadFile",
            title: _t("Upload a file"),
            description: _t("Add a download box"),
            icon: "fa-upload",
            run: this.uploadAndInsertFiles.bind(this),
            isAvailable: this.isUploadCommandAvailable.bind(this),
        },
        powerbox_items: {
            categoryId: "media",
            commandId: "uploadFile",
            keywords: [_t("file"), _t("document")],
        },
        power_buttons: withSequence(5, {
            commandId: "uploadFile",
            description: _t("Upload a file"),
        }),
        unsplittable_node_predicates: (node) => node.classList?.contains("o_file_box"),
        ...(this.config.allowFile && {
            media_dialog_extra_tabs: {
                id: "DOCUMENTS",
                title: _t("Documents"),
                Component: this.componentForMediaDialog,
                sequence: 15,
            },
        }),
        selectors_for_feff_providers: () => ".o_file_box",
        mount_component_handlers: this.setupNewFile.bind(this),
    };

    renderDownloadBox(attachment) {
        return renderEmbeddedFileBox(attachment);
    }

    isUploadCommandAvailable({ anchorNode }) {
        return this.config.allowFile && !closestElement(anchorNode, "[data-embedded='clipboard']");
    }

    get recordInfo() {
        return this.config.getRecordInfo?.() || {};
    }

    get componentForMediaDialog() {
        return EmbeddedFileDocumentsSelector;
    }

    async uploadAndInsertFiles() {
        const attachments = await this.services.uploadLocalFiles.upload(this.recordInfo, {
            multiple: true,
            accessToken: true,
        });
        if (!attachments.length) {
            this.editable.focus();
            return;
        }
        if (this.config.onAttachmentChange) {
            attachments.forEach(this.config.onAttachmentChange);
        }
        const fileCards = attachments.map(this.renderDownloadBox.bind(this));
        fileCards.forEach(this.dependencies.dom.insert);
        this.dependencies.history.addStep();
    }

    setupNewFile({ name, env }) {
        if (name === "file") {
            Object.assign(env, {
                editorShared: {
                    setSelectionAfter: (host) => {
                        try {
                            const leaf = nextLeaf(host, this.editable);
                            if (!leaf) {
                                return;
                            }
                            const leafEl = isBlock(leaf) ? leaf : leaf.parentElement;
                            if (isBlock(leafEl) && leafEl.isContentEditable) {
                                this.dependencies.selection.setSelection({
                                    anchorNode: leafEl,
                                    anchorOffset: 0,
                                });
                            }
                        } catch {
                            return;
                        }
                    },
                },
            });
        }
    }
}
