import { _t } from "@web/core/l10n/translation";
import { FileUploader } from "@web/views/fields/file_handler";
import { patch } from "@web/core/utils/patch";


patch(FileUploader.prototype, {
    async onFileChange(ev) {
        const files = [...ev.target.files].filter(file => this.validFileType(file));
        if (!files.length) {
            return;
        }
        super.onFileChange({ ...ev, target: { ...ev.target, files } });
    },

    /**
    * Validates whether the given file is a PDF when only PDF uploads are allowed.
    *
    * While the `accept` attribute in the file input element suggests valid file types,
    * it does not strictly enforce them. This method provides additional validation
    * to ensure that only PDF files are accepted if `.pdf` is the only allowed extension.
    *
    * If an invalid file type is detected, a notification is displayed to inform the user.
    *
    * @param {File} file - The file to be validated.
    * @returns {boolean} - Returns `true` if the file is a PDF, otherwise `false`.
     */
     validFileType(file) {
        if (
            this.props.acceptedFileExtensions &&
            this.props.acceptedFileExtensions === '.pdf'&&
            file.type !== 'application/pdf'
        ) {
            this.notification.add(
                _t(`Oops! '%(fileName)s' didn’t upload since its format isn’t allowed.`, {
                    fileName: file.name,
                }),
                {
                    type: "danger",
                }
            );
            return false;
        }
        return true;
    },
});
