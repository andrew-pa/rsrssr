
window.postVisit = (itemId) => navigator.sendBeacon(`/visit?id=${itemId}`);

window.showDescriptionDialog = (itemId) => {
    const dialog = document.getElementById(`description-dialog-${itemId}`);
    if (dialog) {
        dialog.showModal();
    }
};

window.closeDescriptionDialog = (itemId) => {
    const dialog = document.getElementById(`description-dialog-${itemId}`);
    if (dialog) {
        dialog.close();
    }
};
