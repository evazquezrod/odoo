from odoo.http import Controller, request, route


class WorkerBundleController(Controller):
    @route("/bus/election_worker_bundle", type="http", auth="public", cors="*")
    def get_election_worker_bundle(self, v=None):  # pylint: disable=unused-argument
        """
        :param str v: Version of the worker, frontend only argument used to
            prevent new worker versions to be loaded from the browser cache.
        """
        bundle_name = "bus.election_worker_assets"
        bundle = request.env["ir.qweb"]._get_asset_bundle(bundle_name, debug_assets="assets" in request.session.debug)
        stream = request.env["ir.binary"]._get_stream_from(bundle.js())
        return stream.get_response(content_security_policy=None)
