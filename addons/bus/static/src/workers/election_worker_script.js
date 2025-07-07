/* eslint-env worker */
/* eslint-disable no-restricted-globals */

import { ElectionWorker } from "./election_worker";

(function () {
    try {
        const electionWorker = new ElectionWorker();
        self.onconnect = function (ev) {
            const currentClient = ev.ports[0];
            const uid = Date.now().toString(36) + Math.random().toString(36).substring(2);
            electionWorker.registerClient(uid, currentClient);
        };
    } catch (error) {
        console.error("ElectionWorker failed to initialize:", error);
    }
})();
