async function apiFetch(url, options = {}) {
    const res = await fetch(url, {
        credentials: 'same-origin',
        ...options,
    });

    if (res.status === 401) {
        window.location.href = '/login';
        throw new Error('Unauthorized');
    }

    return res;
}

async function parseJsonResponse(res, fallbackMessage) {
    if (!res.ok) {
        throw new Error(fallbackMessage);
    }
    return await res.json();
}

async function postJson(url, payload, fallbackMessage) {
    const res = await apiFetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    return await parseJsonResponse(res, fallbackMessage);
}

export async function fetchCampusList() {
    const res = await apiFetch('/campus');
    return await parseJsonResponse(res, 'Error carregant campus');
}

export async function fetchCampusSwitches(name) {
    const res = await apiFetch(`/campus/${encodeURIComponent(name)}/switches`);
    return await parseJsonResponse(res, 'Error carregant switches');
}

export async function fetchFrozenPorts(serial) {
    const res = await apiFetch(`/switch/${encodeURIComponent(serial)}/frozen-ports`);
    return await parseJsonResponse(res, 'Error carregant ports congelats');
}

export async function toggleSwitchPort(serial, port, freeze) {
    const action = freeze ? 'freeze' : 'unfreeze';
    const res = await apiFetch(`/switch/${encodeURIComponent(serial)}/port/${port}/${action}`, {
        method: 'POST',
    });
    if (!res.ok) throw new Error('Error actuant sobre el port');
    return await res.json().catch(() => ({}));
}

export async function syncBatch(serials, nomCampus) {
    return await postJson(
        '/campus/sync-batch',
        { serials, nom_campus: nomCampus },
        'Error sincronitzant',
    );
}

export async function clearBatch(serials, nomCampus) {
    return await postJson(
        '/campus/clear-batch',
        { serials, nom_campus: nomCampus },
        'Error esborrant ACLs',
    );
}

export async function scanAclHits(campus, serials = []) {
    return await postJson(
        `/acl-hits/scan/${encodeURIComponent(campus)}`,
        { serials },
        'Error escanejant ACL hits',
    );
}

export async function fetchPartialHtml(url) {
    const res = await apiFetch(url);
    if (!res.ok) throw new Error(`Error carregant parcial: ${url}`);
    return await res.text();
}
