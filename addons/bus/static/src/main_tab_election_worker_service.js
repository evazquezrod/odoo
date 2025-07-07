import { browser } from "@web/core/browser/browser";
import { Deferred } from "@web/core/utils/concurrency";
import { session } from "@web/session";
import { EventBus } from "@odoo/owl";

export const electionWorkerService = {
    start(env) {
        const bus = new EventBus();
        let worker;
        let id = null;
        let responseDeferred = null;
        let lastHeartbeat = Date.now();
        startWorker();

        function startWorker() {
            const workerURL = `${window.location.origin}/bus/election_worker_bundle?v=${session.election_worker_version}`;
            worker = new browser.SharedWorker(workerURL, {
                name: "odoo:election_worker",
            });
            worker.port.start();
            worker.port.addEventListener("message", messageHandler);
        }

        function send(type, data) {
            worker.port.postMessage({ type, data });
        }

        function messageHandler(messageEv) {
            const timeDiff = Date.now() - lastHeartbeat;
            lastHeartbeat = Date.now();
            console.log("ElectionWorkerService received message:", messageEv.data, timeDiff);
            const { type, data } = messageEv.data;
            switch (type) {
                case "REGISTERED":
                    console.log("ElectionWorkerService registered client:", data.id);
                    id = data.id;
                    break;
                case "MASTER_ID_RESPONSE":
                    if (responseDeferred) {
                        responseDeferred.resolve(data.masterTabId);
                        responseDeferred = null;
                    }
                    break;
                case "HEARTBEAT_REQUEST":
                    send("HEARTBEAT", { id });
                    break;
                case "ASSIGN_MASTER":
                    console.log("This tab is now the master tab:", id);
                    bus.trigger("become_main_tab");
                    break;
                case "UNASSIGN_MASTER":
                    console.log("This tab is no longer the master tab:", id);
                    bus.trigger("no_longer_main_tab");
                    break;
                default:
                    console.warn("ElectionWorkerService received unknown message type:", type);
            }
        }

        async function isOnMainTab() {
            responseDeferred = new Deferred();
            worker.port.postMessage({ type: "WHO_IS_MASTER" });
            const masterId = await responseDeferred;
            return masterId === id;
        }

        return {
            bus: bus,
            isOnMainTab: isOnMainTab,
        };
    },
};
