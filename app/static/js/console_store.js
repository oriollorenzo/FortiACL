export const state = {
    campusList: [],
    currentCampus: null,
    campusCache: new Map(),
    currentSwitches: [],
    selectedSerials: new Set(),
    searchTerm: '',
    sortCol: '',
    sortAsc: true,
    modal: {
        serial: null,
        name: null,
        portCount: 0,
        frozenPorts: new Set(),
    },
};

export function setCampusList(items) {
    state.campusList = Array.isArray(items) ? items : [];
}

export function setCurrentCampus(name) {
    state.currentCampus = name;
}

export function getCampusCache(name) {
    return state.campusCache.get(name) || null;
}

export function setCampusCache(name, payload) {
    state.campusCache.set(name, { ...payload, loadedAt: Date.now() });
}

export function clearCampusCache(name = null) {
    if (name) state.campusCache.delete(name);
    else state.campusCache.clear();
}

export function setCurrentSwitches(items) {
    state.currentSwitches = Array.isArray(items) ? items : [];
}

export function resetInventoryState() {
    state.currentSwitches = [];
    state.selectedSerials.clear();
    state.searchTerm = '';
    state.sortCol = '';
    state.sortAsc = true;
}

export function setSearchTerm(value) {
    state.searchTerm = value || '';
}

export function toggleSelectedSerial(serial, checked) {
    if (checked) state.selectedSerials.add(serial);
    else state.selectedSerials.delete(serial);
}

export function replaceSelectedSerials(serials) {
    state.selectedSerials = new Set(serials || []);
}

export function setSort(col) {
    if (state.sortCol === col) state.sortAsc = !state.sortAsc;
    else {
        state.sortCol = col;
        state.sortAsc = true;
    }
}

export function setModalState({ serial, name, portCount, frozenPorts }) {
    state.modal = {
        serial,
        name,
        portCount,
        frozenPorts: new Set(frozenPorts || []),
    };
}

export function setPortFrozen(port, frozen) {
    if (frozen) state.modal.frozenPorts.add(port);
    else state.modal.frozenPorts.delete(port);
}

export function updateFrozenCount(serial, count) {
    const sw = state.currentSwitches.find(x => x.serial === serial);
    if (sw) sw.ports_congelats_count = count;

    const cached = state.campusCache.get(state.currentCampus);
    if (cached?.switches) {
        const swc = cached.switches.find(x => x.serial === serial);
        if (swc) swc.ports_congelats_count = count;
    }
}
