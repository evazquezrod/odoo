import { debounce, Deferred } from "@bus/workers/websocket_worker_utils";

export class ElectionWorker {
    MAIN_TAB_TIMEOUT_PERIOD = 3000; // 3 seconds

    constructor() {
        this.masterTabId = null;
        this.clients = {};
        this.lastHeartbeat = Date.now();
        this.electionDeferred = null;
        this.debouncedReturnMasterId = debounce(this.returnMasterId.bind(this), 300);
        this.heartbeatCheckInterval;
        this.heartbeatRequestInterval;
    }

    registerClient(id, messagePort) {
        messagePort.onmessage = (ev) => {
            this.handleMessage(ev);
        };
        this.clients[id] = messagePort;
        console.log("ElectionWorker registered client:", id);
        messagePort.postMessage({
            type: "REGISTERED",
            data: {
                id: id,
            },
        });
        if (Object.keys(this.clients).length === 1) {
            this.startElection();
        }
    }

    unregisterClient(id) {
        if (this.clients[id]) {
            this.clients[id].close();
            delete this.clients[id];
            console.log("ElectionWorker unregistered client:", id);
        } else {
            console.warn("Client not found for unregistration:", id);
        }
    }

    broadcast(message) {
        for (const client of Object.values(this.clients)) {
            client.postMessage(message);
        }
    }

    sendMessage(id, message) {
        if (id in this.clients) {
            this.clients[id].postMessage(message);
        } else {
            console.warn("Client id not registered:", id);
        }
    }

    requestHeartbeat(id) {
        if (id) {
            this.sendMessage(id, {
                type: "HEARTBEAT_REQUEST",
            });
        } else {
            this.broadcast({
                type: "HEARTBEAT_REQUEST",
            });
        }
    }

    async returnMasterId() {
        if (this.electionDeferred) {
            await this.electionDeferred;
        }
        this.broadcast({
            type: "MASTER_ID_RESPONSE",
            data: {
                masterTabId: this.masterTabId,
            },
        });
    }

    startElection() {
        this.electionDeferred = new Deferred();
        console.log("ElectionWorker starting election");
        this.lastHeartbeat = Date.now();
        this.requestHeartbeat();
    }

    finishElection(id) {
        console.log("ElectionWorker finishing election with id:", id);
        this.masterTabId = id;
        this.sendMessage(id, {
            type: "ASSIGN_MASTER",
        });
        this.electionDeferred.resolve();
        this.electionDeferred = null;
        clearInterval(this.heartbeatCheckInterval);
        clearInterval(this.heartbeatRequestInterval);
        this.heartbeatCheckInterval = setInterval(() => {
            const now = Date.now();
            console.log("ElectionWorker checking master tab heartbeat: ", now - this.lastHeartbeat);
            if (now - this.lastHeartbeat > this.MAIN_TAB_TIMEOUT_PERIOD) {
                console.log("Master tab heartbeat timeout, starting new election");
                this.startElection();
            }
        }, this.MAIN_TAB_TIMEOUT_PERIOD);
        this.heartbeatRequestInterval = setInterval(() => {
            this.requestHeartbeat(this.masterTabId);
        }, this.MAIN_TAB_TIMEOUT_PERIOD / 2);
    }

    handleMessage(event) {
        const { type, data } = event.data;
        console.log("ElectionWorker received message:", type, data);
        switch (type) {
            // case "REGISTER":
            //     this.registerClient(event.source);
            //     break;
            case "UNREGISTER":
                this.unregisterClient(event.source);
                break;
            case "WHO_IS_MASTER":
                this.debouncedReturnMasterId();
                break;
            case "HEARTBEAT":
                if (this.electionDeferred) {
                    this.finishElection(data.id);
                } else if (this.masterTabId === data.id) {
                    this.lastHeartbeat = Date.now();
                }
                break;
            default:
                console.warn("Unknown message type:", type);
        }
    }
}
