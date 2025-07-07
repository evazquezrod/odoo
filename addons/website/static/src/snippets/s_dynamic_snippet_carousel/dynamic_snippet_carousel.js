import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";
import { utils as uiUtils } from "@web/core/ui/ui_service";
import { markup } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class DynamicSnippetCarousel extends DynamicSnippet {
    static selector = ".s_dynamic_snippet_carousel";

    setup() {
        super.setup();
        this.templateKey = "website.s_dynamic_snippet.carousel";
        this.offset = 0;
        this.fetchedData = [];
        this.hasMore = true;
        this.totalToFetch = 0;
        this.chunkSize = 16;
        this.intersectionObserver = null;
    }

    async willStart() {
        const { numberOfRecords } = this.el.dataset;
        this.totalToFetch = parseInt(numberOfRecords);
        this.offset = 0;
        this.fetchedData = [];
        this.hasMore = true;
        await this.fetchMoreData();
    }

    start() {
        this.render();
        this.setupLazyLoadObserver();
    }

    destroy() {
        this.intersectionObserver?.disconnect();
        super.destroy();
    }

    async fetchMoreData() {
        if (!this.hasMore) return;

        const limit = Math.min(this.chunkSize, this.totalToFetch - this.fetchedData.length);
        if (limit <= 0) {
            this.hasMore = false;
            return;
        }

        const newData = await this._fetchFilteredData({ limit, offset: this.offset });
        const newFragments = newData.map(markup);

        this.fetchedData.push(...newFragments);
        this.data = this.fetchedData;
        this.offset += limit;

        if (this.fetchedData.length >= this.totalToFetch || newFragments.length < limit) {
            this.hasMore = false;
        }
    }

    async _fetchFilteredData({ limit, offset }) {
        const nodeData = this.el.dataset;
        const params = {
            filter_id: parseInt(nodeData.filterId),
            template_key: nodeData.templateKey,
            limit,
            offset,
            ...this.getRpcParameters(),
            ...JSON.parse(this.el.dataset?.customTemplateData || "{}"),
        };
        return rpc("/website/snippet/filters", params);
    }

    render() {
        const templateAreaEl = this.el.querySelector(".dynamic_snippet_template");
        const carouselEl = templateAreaEl.querySelector(".carousel");
        const carouselInner = carouselEl?.querySelector(".carousel-inner");

        let activeIndex = 0;
        if (carouselInner) {
            const slides = Array.from(carouselInner.children);
            activeIndex = slides.findIndex((el) => el.classList.contains("active"));
        }

        this.isVisible = !!(this.data.length || this.withSample);
        this.prepareContent();

        this.services["public.interactions"].stopInteractions(templateAreaEl);
        templateAreaEl.replaceChildren(this.renderedContentNode);
        this.services["public.interactions"].startInteractions(templateAreaEl);

        this.waitForTimeout(() => {
            const newSlides = templateAreaEl.querySelectorAll(".carousel-item");
            if (newSlides.length) {
                newSlides.forEach((el) => el.classList.remove("active"));
                newSlides[Math.min(activeIndex, newSlides.length - 1)].classList.add("active");
            }

            if (carouselEl) {
                carouselEl.classList.add("carousel-fade");
                carouselEl.dataset.bsRide = "false";
                carouselEl.dataset.bsInterval = "false";

                const interval = parseInt(this.el.dataset.carouselInterval);
                if (!isNaN(interval) && interval > 0) {
                    carouselEl.dataset.bsRide = "carousel";
                    carouselEl.dataset.bsInterval = interval.toString();
                }
            }
        }, 0);
    }

    setupLazyLoadObserver() {
        const templateAreaEl = this.el.querySelector(".dynamic_snippet_template");
        const lastSlide = templateAreaEl?.querySelector(".carousel-inner > .carousel-item:last-child");
        if (!lastSlide) return;

        this.intersectionObserver?.disconnect();

        this.intersectionObserver = new IntersectionObserver(async (entries) => {
            for (const entry of entries) {
                if (entry.isIntersecting && this.hasMore) {
                    this.intersectionObserver.unobserve(entry.target);
                    await this.fetchMoreData();
                    this.render();
                    this.setupLazyLoadObserver();
                    break;
                }
            }
        }, {
            root: null,
            threshold: 0.01,
        });

        this.intersectionObserver.observe(lastSlide);

        const rect = lastSlide.getBoundingClientRect();
        if (rect.top < window.innerHeight && rect.bottom > 0) {
            this.intersectionObserver.takeRecords().forEach(async (entry) => {
                if (entry.isIntersecting && this.hasMore) {
                    this.intersectionObserver.unobserve(entry.target);
                    await this.fetchMoreData();
                    this.render();
                    this.setupLazyLoadObserver();
                }
            });
        }
    }

    getQWebRenderOptions() {
        const scrollMode = this.el.classList.contains('o_carousel_multi_items') ? 'single' : 'all';
        return Object.assign(
            super.getQWebRenderOptions(...arguments),
            {
                interval: parseInt(this.el.dataset.carouselInterval),
                rowPerSlide: parseInt(uiUtils.isSmall() ? 1 : this.el.dataset.rowPerSlide || 1),
                arrowPosition: this.el.dataset.arrowPosition || "",
                scrollMode: scrollMode,
            },
        );
    }
}

registry
    .category("public.interactions")
    .add("website.dynamic_snippet_carousel", DynamicSnippetCarousel);
