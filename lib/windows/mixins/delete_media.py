# coding=utf-8
from lib import util
from lib.i18n import T
from lib.windows import optionsdialog, busy


class DeleteMediaMixin(object):
    def delete(self, item=None):
        item = item or self.mediaItem
        if not optionsdialog.confirmDelete(item):
            return

        if not self._delete(item=item):
            util.messageDialog(T(32330, 'Message'), T(32331, 'There was a problem while attempting to delete the media.'))
            return
        return True

    @busy.dialog()
    def _delete(self, item, do_close=False):
        success = item.delete()
        util.LOG('Media DELETE: {0} - {1}', item, success and 'SUCCESS' or 'FAILED')
        if success and do_close:
            self.doClose()
        return success
