import {
    state,
    setCampusList,
    setCurrentCampus,
    getCampusCache,
    setCampusCache,
    setCurrentSwitches,
    resetInventoryState,
    setSearchTerm,
    toggleSelectedSerial,
    replaceSelectedSerials,
    setSort,
    setModalState,
    setPortFrozen,
    updateFrozenCount,
    clearCampusCache,
} from './console_store.js';

import {
    fetchCampusList,
    fetchCampusSwitches,
    fetchFrozenPorts,
    toggleSwitchPort,
    syncBatch,
    clearBatch,
    scanAclHits,
} from './console_api.js';

import { activateMenuButton, showPanel } from './app_shell.js';


const FORBIDDEN_PORTS = new Set([49, 50, 51, 52, 1048, 2048]);


function byId(id) {
    return document.getElementById(id);
}

function setLoading(on, text = 'Processant operacio...') {
    const loadingText = byId('loading-text');
    const loadingOverlay = byId('loading-overlay');

    if (loadingText) loadingText.innerText = text;
    if (loadingOverlay) loadingOverlay.classList.toggle('hidden', !on);
}

function hidePortsModal() {
    const modal = byId('ports-modal');
    if (modal) modal.classList.add('hidden');
}

function campusButtonHtml(name) {
    return `
        <button data-campus="${name}"
                class="campus-trigger w-full text-left flex items-center gap-3 px-3 py-2.5 text-sm font-medium text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-md transition">
            <i class="fas fa-building text-zinc-500"></i>
            <span>${name.replace(/_/g, ' ')}</span>
        </button>
    `;
}

function getStatusDot(status) {
    const normalized = (status || '').toLowerCase();

    if (
        normalized.includes('connected') ||
        normalized.includes('online') ||
        normalized.includes('up') ||
        normalized.includes('ok')
    ) {
        return 'bg-green-500';
    }

    if (normalized.includes('warning')) return 'bg-yellow-500';
    return 'bg-red-500';
}

function getSyncBadge(sw) {
    if (sw.acls_sincronitzades === true) {
        return '<span class="forti-badge bg-emerald-900 text-emerald-200 border border-emerald-700">ok</span>';
    }
    if (sw.acls_sincronitzades === false) {
        return '<span class="forti-badge bg-amber-900 text-amber-200 border border-amber-700">pendent</span>';
    }
    return '<span class="forti-badge bg-zinc-800 text-zinc-300 border border-zinc-700">n/d</span>';
}

function inferPortCount(model) {
    const text = model || '';
    if (text.includes('108')) return 8;
    if (text.includes('124') || text.includes('224') || text.includes('24')) return 24;
    return 48;
}

function compareValues(a, b) {
    if (a === b) return 0;
    return String(a ?? '').localeCompare(String(b ?? ''), 'ca', {
        numeric: true,
        sensitivity: 'base',
    });
}

function filteredSwitches() {
    let items = [...state.currentSwitches];
    const query = state.searchTerm.trim().toLowerCase();

    if (query) {
        items = items.filter(sw => {
            const haystack = `${sw.name || ''} ${sw.serial || ''} ${sw.model_profile || ''}`.toLowerCase();
            return haystack.includes(query);
        });
    }

    if (state.sortCol) {
        items.sort((a, b) => {
            const result = compareValues(a[state.sortCol], b[state.sortCol]);
            return state.sortAsc ? result : -result;
        });
    }

    return items;
}

function syncSortIndicators() {
    document.querySelectorAll('span[id^="sort-"]').forEach(node => {
        node.innerText = '';
    });

    if (!state.sortCol) return;

    const node = byId(`sort-${state.sortCol}`);
    if (node) node.innerText = state.sortAsc ? '↑' : '↓';
}

function syncMasterCheckbox() {
    const master = byId('select-all');
    if (!master) return;

    const visible = Array.from(document.querySelectorAll('.sw-checkbox'));
    master.checked = visible.length > 0 && visible.every(cb => cb.checked);
}

function renderCampusTree() {
    const tree = byId('campus-tree');
    if (!tree) return;

    tree.innerHTML = state.campusList.map(campusButtonHtml).join('');

    tree.querySelectorAll('[data-campus]').forEach(btn => {
        btn.addEventListener('click', async () => {
            activateMenuButton(btn);
            await loadCampus(btn.dataset.campus, false);
        });
    });
}

function buildSwitchRow(sw) {
    return `
        <tr class="hover-row transition text-sm">
            <td class="p-4 text-center border-b border-zinc-800">
                <input type="checkbox" class="sw-checkbox rounded border-zinc-600 bg-zinc-800 text-red-600"
                       data-serial="${sw.serial}" ${state.selectedSerials.has(sw.serial) ? 'checked' : ''}>
            </td>
            <td class="p-4 font-bold border-b border-zinc-800">${sw.name || ''}</td>
            <td class="p-4 text-zinc-400 text-xs border-b border-zinc-800">${sw.model_profile || ''}</td>
            <td class="p-4 text-zinc-500 text-xs font-mono border-b border-zinc-800">${sw.serial || ''}</td>
            <td class="p-4 text-center border-b border-zinc-800">
                <span class="inline-block w-2 h-2 rounded-full ${getStatusDot(sw.status)} mr-2"></span>${sw.status || ''}
            </td>
            <td class="p-4 text-center text-zinc-400 text-xs border-b border-zinc-800 italic">${sw.versio_acl || ''}</td>
            <td class="p-4 text-center border-b border-zinc-800">${getSyncBadge(sw)}</td>
            <td class="p-4 text-center border-b border-zinc-800">
                <button class="text-sky-400 hover:text-sky-200 font-bold"
                        data-open-ports="${sw.serial}"
                        data-name="${encodeURIComponent(sw.name || '')}"
                        data-port-count="${inferPortCount(sw.model_profile)}">
                    <span class="mr-2">Ports:</span>${sw.ports_congelats_count || 0}
                </button>
            </td>
        </tr>
    `;
}

function bindSwitchTableEvents() {
    document.querySelectorAll('.sw-checkbox').forEach(cb => {
        cb.addEventListener('change', () => {
            toggleSelectedSerial(cb.dataset.serial, cb.checked);
            syncMasterCheckbox();
        });
    });

    document.querySelectorAll('[data-open-ports]').forEach(btn => {
        btn.addEventListener('click', () => {
            openFrozenPorts(
                btn.dataset.openPorts,
                decodeURIComponent(btn.dataset.name),
                Number(btn.dataset.portCount),
            );
        });
    });
}

function renderSwitchTable() {
    const tbody = byId('switches-body');
    if (!tbody) return;

    const items = filteredSwitches();

    if (!items.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="p-12 text-center text-zinc-500 italic">
                    No hi ha resultats per als filtres actuals.
                </td>
            </tr>
        `;
        syncMasterCheckbox();
        return;
    }

    tbody.innerHTML = items.map(buildSwitchRow).join('');
    bindSwitchTableEvents();
    syncMasterCheckbox();
}

function renderPortsModal() {
    const { serial, name, portCount, frozenPorts } = state.modal;
    const title = byId('ports-modal-title');
    const grid = byId('ports-grid');
    const modal = byId('ports-modal');

    if (!title || !grid || !modal) return;

    title.innerText = `Ports del switch: ${name}`;

    let html = '';
    for (let i = 1; i <= portCount; i++) {
        if (FORBIDDEN_PORTS.has(i)) continue;

        const isFrozen = frozenPorts.has(i);
        html += `
            <div data-port="${i}"
                 class="p-2 rounded border text-center cursor-pointer transition text-xs flex flex-col items-center justify-center min-h-[50px]
                 ${isFrozen ? 'bg-sky-900 border-sky-500 text-white shadow-lg' : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-sky-400'}">
                <span class="opacity-30 text-[8px] uppercase font-bold">p</span>
                <span class="font-bold">${i}</span>
                ${isFrozen ? '<i class="fas fa-snowflake block text-[8px] mt-1 text-sky-300"></i>' : ''}
            </div>
        `;
    }

    grid.innerHTML = html;
    modal.classList.remove('hidden');

    grid.querySelectorAll('[data-port]').forEach(node => {
        node.addEventListener('click', async () => {
            const port = Number(node.dataset.port);
            const isFrozen = state.modal.frozenPorts.has(port);
            await togglePort(port, serial, isFrozen);
        });
    });
}

async function openFrozenPorts(serial, name, portCount) {
    try {
        const frozen = await fetchFrozenPorts(serial);
        setModalState({ serial, name, portCount, frozenPorts: frozen });
        renderPortsModal();
    } catch (e) {
        console.error(e);
        alert('Error carregant ports congelats');
    }
}

async function togglePort(port, serial, isFrozen) {
    try {
        await toggleSwitchPort(serial, port, !isFrozen);
        setPortFrozen(port, !isFrozen);
        updateFrozenCount(serial, state.modal.frozenPorts.size);
        renderPortsModal();
        renderSwitchTable();
    } catch (e) {
        console.error(e);
        alert('Error actuant sobre el port');
    }
}

async function refreshCurrentCampus() {
    if (!state.currentCampus) return;
    clearCampusCache(state.currentCampus);
    await loadCampus(state.currentCampus, true);
}

async function handleSyncSelected() {
    const serials = Array.from(state.selectedSerials);
    if (!serials.length) {
        alert('Selecciona almenys un switch');
        return;
    }

    setLoading(true, 'Sincronitzant switches...');
    try {
        await syncBatch(serials, state.currentCampus);
        clearCampusCache(state.currentCampus);
        await loadCampus(state.currentCampus, true);
    } catch (e) {
        console.error(e);
        alert('Error sincronitzant');
    } finally {
        setLoading(false);
    }
}

async function handleClearSelected() {
    const serials = Array.from(state.selectedSerials);
    if (!serials.length) {
        alert('Selecciona almenys un switch');
        return;
    }
    if (!confirm('Esborrar ACLs dels switches seleccionats?')) return;

    setLoading(true, 'Esborrant ACLs...');
    try {
        await clearBatch(serials, state.currentCampus);
        clearCampusCache(state.currentCampus);
        await loadCampus(state.currentCampus, true);
    } catch (e) {
        console.error(e);
        alert('Error esborrant ACLs');
    } finally {
        setLoading(false);
    }
}

async function handleSyncAll() {
    if (!state.currentSwitches.length) return;
    replaceSelectedSerials(state.currentSwitches.map(sw => sw.serial));
    renderSwitchTable();
    await handleSyncSelected();
}

async function handleScanAclHits() {
    if (!state.currentCampus) {
        alert('Primer selecciona un campus');
        return;
    }

    const serials = Array.from(state.selectedSerials);
    if (!serials.length) {
        alert('Has de seleccionar almenys un switch');
        return;
    }

    setLoading(true, 'Escanejant ACL hits...');
    try {
        await scanAclHits(state.currentCampus, serials);
        alert('Escaneig ACL hits finalitzat');
    } catch (e) {
        console.error(e);
        alert('Error escanejant ACL hits');
    } finally {
        setLoading(false);
    }
}

export async function bootstrapInventory() {
    const data = await fetchCampusList();
    setCampusList(data.campus_disponibles || []);
    renderCampusTree();
    syncSortIndicators();
}

export async function loadCampus(name, force = false) {
    showPanel('inventory', 'Inventari', `Campus actiu: ${name.replace(/_/g, ' ')}`);
    setCurrentCampus(name);

    const cached = getCampusCache(name);
    if (cached && !force) {
        resetInventoryState();
        setCurrentSwitches(cached.switches || []);
        renderSwitchTable();
        return;
    }

    setLoading(true, 'Carregant inventari del campus...');
    try {
        const data = await fetchCampusSwitches(name);
        setCampusCache(name, data);
        resetInventoryState();
        setCurrentSwitches(data.switches || []);
        renderSwitchTable();
    } catch (e) {
        console.error(e);
        alert('Error carregant switches del campus');
    } finally {
        setLoading(false);
    }
}

export function bindInventoryEvents() {
    const searchInput = byId('switch-search');
    if (searchInput) {
        searchInput.addEventListener('input', e => {
            setSearchTerm(e.target.value);
            renderSwitchTable();
        });
    }

    document.querySelectorAll('[data-sort-col]').forEach(th => {
        th.addEventListener('click', () => {
            setSort(th.dataset.sortCol);
            syncSortIndicators();
            renderSwitchTable();
        });
    });

    const selectAll = byId('select-all');
    if (selectAll) {
        selectAll.addEventListener('change', e => {
            const serials = filteredSwitches().map(sw => sw.serial);
            replaceSelectedSerials(e.target.checked ? serials : []);
            renderSwitchTable();
        });
    }

    byId('refresh-campus-btn')?.addEventListener('click', refreshCurrentCampus);
    byId('sync-selected-btn')?.addEventListener('click', handleSyncSelected);
    byId('clear-selected-btn')?.addEventListener('click', handleClearSelected);
    byId('sync-all-btn')?.addEventListener('click', handleSyncAll);
    byId('scan-acl-hits-btn')?.addEventListener('click', handleScanAclHits);
    byId('close-ports-modal-x')?.addEventListener('click', hidePortsModal);
    byId('close-ports-modal-btn')?.addEventListener('click', hidePortsModal);
}
