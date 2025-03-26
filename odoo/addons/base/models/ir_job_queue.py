import logging

from odoo import api, fields, models
from odoo.fields import Domain

_logger = logging.getLogger(__name__)


class JobQueueMixin(models.AbstractModel):
    _name = 'job.queue.mixin'
    _description = "Job Queue Mixin"

    @api.model
    def _cron_process_queue(self, *, condition=Domain.TRUE, limit=1000):
        precondition = self._queue_precondition()
        records = self.search(condition & precondition, limit=limit)
        cron = self.env['ir.cron']
        cron._commit_progress(remaining=len(records) if len(records) < limit else self.search_count(precondition))
        cron._job_queue_process(
            records,
            precondition=precondition,
            process=self._queue_process.__func__,
            error_handler=self._queue_process_error.__func__,
            allow_referencing=True,
        )

    @api.model
    def _queue_precondition(self):
        return Domain.TRUE

    def _queue_process(self):
        self.ensure_one()
        raise NotImplementedError

    def _queue_process_error(self, exception):
        raise NotImplementedError

    def _process_now(self):
        self.env['ir.cron']._job_queue_process(
            self,
            precondition=self._queue_precondition(),
            process=self._queue_process.__func__,
            error_handler=self._queue_process_error.__func__,
            allow_referencing=True,
        )

    def _process_post_transaction(self, ignore_errors=True):
        if not self:
            return

        def queue_in_postcommit():
            try:
                with self.env.registry.cursor() as cr:
                    self.with_env(self.env(cr=cr))._process_now()
            except Exception:
                if ignore_errors:
                    _logger.exception("Error in post-transaction on queue for %s", self)
                    return
                raise

        postcommit = self.env.cr.postcommit
        postcommit.add(queue_in_postcommit)


class TestQueue(models.Model):
    _name = _description = 'test.queue'
    _inherit = ['job.queue.mixin']
    run_at = fields.Datetime(default=lambda s: s.env.cr.now())

    @api.model
    def _queue_precondition(self):
        return Domain('run_at', '<=', self.env.cr.now())

    def _queue_process(self):
        self.ensure_one()
        _logger.info("%s", self)
        self.run_at = False

    def _queue_process_error(self, exception):
        self.run_at = False
        _logger.error("Ah...", exc_info=exception)

    def test_process_now(self):
        records = self.create([{}, {}])
        records._process_now()

    def test_process_post(self):
        records = self.create([{}, {}])
        records._process_post_transaction()

    def test_custom(self):
        records = self.create([{}, {}])

        def dostuff(rec):
            _logger.info(rec.read())
        self.env['ir.cron']._job_queue_process(
            records, dostuff, Domain.TRUE,
            error_handler=lambda x, e: None,
        )
