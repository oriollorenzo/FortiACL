import { activateMenuButton, showEmbeddedPanel } from './app_shell.js';

export function bindEmbeddedPanelTriggers() {
    document.querySelectorAll('[data-panel-trigger="embedded"]').forEach(btn => {
        btn.addEventListener('click', () => {
            activateMenuButton(btn);
            showEmbeddedPanel({
                title: btn.dataset.panelTitle || btn.innerText.trim(),
                subtitle: btn.dataset.panelSubtitle || '',
                url: btn.dataset.iframeSrc,
            });
        });
    });
}
