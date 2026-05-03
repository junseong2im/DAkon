/* ============================================================
   WebSocket Simulator — Connection Status
   ============================================================ */

const WebSocketSim = (() => {
  let interval = null;
  let status = 'connected';

  function start() {
    Store.setWsStatus('connected');
    status = 'connected';

    /* Simulate occasional disconnections */
    interval = setInterval(() => {
      if (status === 'connected' && Math.random() < 0.08) {
        status = 'disconnected';
        Store.setWsStatus('disconnected');
        Toast.show('WebSocket 연결이 끊어졌습니다. 재연결 시도 중...', 'warning');

        /* Auto-reconnect after 3-5 seconds */
        setTimeout(() => {
          status = 'connected';
          Store.setWsStatus('connected');
          Toast.show('WebSocket 재연결 완료', 'success');
        }, 3000 + Math.random() * 2000);
      }
    }, 10000);
  }

  function stop() {
    if (interval) clearInterval(interval);
    interval = null;
  }

  function getStatus() {
    return status;
  }

  return { start, stop, getStatus };
})();
