/* Installation status belongs to the browser; gameplay remains in Ren'Py. */
(() => {
    const status = document.getElementById('offlineStatus');
    const install = document.getElementById('installPwa');
    let installPrompt;
    let owner;
    let preparedUpdate;
    window.addEventListener('beforeinstallprompt', event => {
        event.preventDefault(); installPrompt = event; install.hidden = false;
    });
    install.addEventListener('click', async () => {
        if (!installPrompt) return;
        await installPrompt.prompt(); await installPrompt.userChoice;
        installPrompt = null; install.hidden = true;
    });
    window.addEventListener('appinstalled', () => { install.hidden = true; });
    async function check() {
        if (!owner?.active) return;
        const expected = new URL('./service-worker.js', location.href).href;
        if (owner.scope !== new URL('./', location.href).href || owner.active.scriptURL !== expected) return;
        const channel = new MessageChannel();
        channel.port1.onmessage = event => {
            window.rainOfflineReady = event.data.ready;
            window.rainOfflineRevision = event.data.revision;
            status.textContent = owner.waiting || preparedUpdate?.state === 'installed' ? '新版已准备，请关闭此应用的所有窗口后重开' :
                event.data.ready ? '完整内容已保存，可离线重开' : '正在保存离线内容…';
            status.dataset.ready = String(event.data.ready);
            channel.port1.close();
        };
        owner.active.postMessage({type: 'RAIN_OFFLINE_STATUS'}, [channel.port2]);
    }
    function watchWorker(worker) {
        if (!worker) return;
        const changed = () => {
            // At the installed event the registration's waiting property may
            // update on the next task. An installed replacement already has
            // the same verified complete cache and must wait for old clients.
            if (worker.state === 'installed' && owner.active && owner.active !== worker) preparedUpdate = worker;
            if (worker.state === 'activated' || worker.state === 'redundant') {
                if (preparedUpdate === worker) preparedUpdate = null;
            }
            if (worker.state === 'redundant') status.textContent = '离线保存未完成；联网后重新打开可重试';
            if (worker.state === 'installed' || worker.state === 'activated') check();
        };
        worker.addEventListener('statechange', changed);
        changed();
    }
    if (!('serviceWorker' in navigator)) {
        status.textContent = '此浏览器不支持离线安装，建议使用最新版浏览器'; return;
    }
    navigator.serviceWorker.addEventListener('controllerchange', check);
    navigator.serviceWorker.register('./service-worker.js', {scope: './', updateViaCache: 'none'})
        .then(registration => {
            owner = registration;
            registration.addEventListener('updatefound', () => watchWorker(registration.installing));
            // Registration can finish after updatefound has already fired.
            watchWorker(registration.installing);
            watchWorker(registration.waiting);
            check();
        }).catch(() => { status.textContent = '离线保存未完成；联网后重新打开可重试'; });
})();
