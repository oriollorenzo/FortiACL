const shellState = {
    activePanel: 'inventory',
};

function byId(id) {
    return document.getElementById(id);
}

function hideAllPanels() {
    document.querySelectorAll('.panel-view').forEach(p => p.classList.add('panel-hidden'));
}

function clearActiveMenuItems() {
    document.querySelectorAll('.panel-trigger, .campus-trigger').forEach(el => {
        el.classList.remove('menu-item-active');
    });
}

export function initAccordionMenu() {
    document.querySelectorAll('[data-group-toggle]').forEach(btn => {
        btn.addEventListener('click', () => {
            const group = btn.dataset.groupToggle;
            const wrapper = document.querySelector(`[data-group="${group}"]`);
            const body = document.querySelector(`[data-group-body="${group}"]`);
            const open = wrapper.classList.contains('tree-open');

            wrapper.classList.toggle('tree-open', !open);
            body.classList.toggle('hidden', open);
        });
    });
}

export function activateMenuButton(node) {
    clearActiveMenuItems();
    if (node) node.classList.add('menu-item-active');
}

export function showPanel(panelName, title, subtitle = '') {
    hideAllPanels();

    const panel = byId(`panel-${panelName}`);
    if (panel) panel.classList.remove('panel-hidden');

    byId('page-title').innerText = title;
    byId('page-subtitle').innerText = subtitle;

    const inventoryToolbar = byId('inventory-toolbar');
    inventoryToolbar.classList.toggle('hidden', panelName !== 'inventory');

    shellState.activePanel = panelName;
}

export function showEmbeddedPanel({ title, subtitle, url }) {
    showPanel('embedded', title, subtitle);
    const frame = byId('embedded-frame');
    if (frame && frame.src !== url) {
        frame.src = url;
    }
}
