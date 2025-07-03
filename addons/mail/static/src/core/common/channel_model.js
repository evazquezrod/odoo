import { fields, Record } from "@mail/core/common/record";

export class Channel extends Record {
    static id = "id";
    static _name = "discuss.channel";

    static async getOrFetch(data, fieldNames = []) {
        let channel = this.get(data);
        if (
            data.id > 0 &&
            (!channel || fieldNames.some((fieldName) => channel[fieldName] === undefined))
        ) {
            await this.store.fetchStoreData("mail.thread", {
                thread_model: "discuss.channel",
                thread_id: data.id,
                request_list: fieldNames,
            });
            channel = this.get(data);
            if (!channel.exists() || !channel.hasReadAccess) {
                return;
            }
        }
        return channel;
    }

    storeAsAllChannels = fields.One("Store", {
        compute() {
            return this.store;
        },
        eager: true,
    });
}

Channel.register();
