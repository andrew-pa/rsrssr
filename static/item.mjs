
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
// Send a POST to dismiss the item, then reload the page
window.postDismiss = (itemId) => {
    fetch(`/dismiss?id=${itemId}`, { method: 'POST' })
        .then(() => { window.location.reload(); })
        .catch((err) => { console.error('Dismiss failed:', err); });
    return false;
};
