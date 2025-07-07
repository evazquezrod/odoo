import { browser } from "@web/core/browser/browser";
import { isIosApp } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { multiTabService } from "@bus/multi_tab_service";
import { electionWorkerService } from "@bus/main_tab_election_worker_service";

registry
    .category("services")
    .add("main_tab", browser.SharedWorker && !isIosApp() ? electionWorkerService : multiTabService);
