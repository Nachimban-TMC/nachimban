/* 푸시 알림 — 허용 요청 → 구독 → 서버 저장 */
(function () {
  var VAPID_PUBLIC = window.NB_VAPID_PUBLIC || '';
  var API = '/api/subscribe';

  function b64ToU8(b64) {
    var pad = '='.repeat((4 - (b64.length % 4)) % 4);
    var s = (b64 + pad).replace(/-/g, '+').replace(/_/g, '/');
    var raw = atob(s), arr = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
    return arr;
  }

  var supported = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
  // iOS 는 홈 화면에 추가한 경우에만 푸시 가능
  var standalone = window.matchMedia('(display-mode: standalone)').matches ||
                   window.navigator.standalone === true;
  var isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);

  function setState(el, cls, html) {
    if (!el) return;
    el.className = 'pushbox ' + cls;
    el.innerHTML = html;
  }


  // ── 자가 복구 ────────────────────────────────────────────────────────────
  // 구독은 여러 이유로 조용히 끊긴다(브라우저의 구독 회전, 서버에서 만료 정리,
  // iOS 재설치 등). 그때마다 사용자에게 "다시 구독을 눌러달라"고 할 수는 없다.
  // 그래서 앱을 열 때마다 아래를 자동으로 한다 — 사용자는 아무것도 안 한다.
  //   1) 알림이 이미 허용돼 있는데 구독이 없으면  → 조용히 다시 구독
  //   2) 구독이 있으면                          → 서버에 다시 저장(있으면 갱신, 지워졌으면 복구)
  //   3) 구독의 서버키가 현재 키와 다르면        → 해지 후 새로 구독
  function u8ToB64url(buf) {
    var b = new Uint8Array(buf), s = '';
    for (var i = 0; i < b.length; i++) s += String.fromCharCode(b[i]);
    return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }

  function saveSub(sub) {
    return fetch(API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subscription: sub })
    }).catch(function () {});
  }

  function subscribeNow(reg) {
    return reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: b64ToU8(VAPID_PUBLIC)
    }).then(saveSub);
  }

  window.nbPushHeal = function () {
    if (!supported || !VAPID_PUBLIC) return;
    if (isIOS && !standalone) return;                 // iOS 는 설치된 앱에서만
    if (Notification.permission !== 'granted') return; // 허용 안 했으면 건드리지 않는다
    navigator.serviceWorker.ready.then(function (reg) {
      return reg.pushManager.getSubscription().then(function (sub) {
        if (!sub) return subscribeNow(reg);           // 1) 끊겼으면 조용히 재구독
        var key = sub.options && sub.options.applicationServerKey;
        if (key && u8ToB64url(key) !== VAPID_PUBLIC) { // 3) 서버키가 바뀌었으면 갈아끼움
          return sub.unsubscribe().then(function () { return subscribeNow(reg); });
        }
        return saveSub(sub);                          // 2) 살아있으면 서버에 재등록
      });
    }).catch(function () {});
  };

  // 앱을 열 때와 다시 앞으로 나올 때마다 점검한다.
  if (document.readyState === 'complete') setTimeout(window.nbPushHeal, 1500);
  else window.addEventListener('load', function () { setTimeout(window.nbPushHeal, 1500); });
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) window.nbPushHeal();
  });

  window.nbPushInit = function () {
    var box = document.getElementById('pushbox');
    if (!box) return;

    if (!supported) {
      setState(box, 'off', '<span class="pl">알림</span><span class="pd">이 브라우저는 푸시 알림을 지원하지 않습니다.</span>');
      return;
    }
    if (isIOS && !standalone) {
      setState(box, 'off',
        '<span class="pl">앱 알림</span><span class="pd">아이폰은 앱으로 설치해야 알림을 받을 수 있어요.<br>' +
        '① 아래 <b>공유 ⬆️</b> → ② <b>홈 화면에 추가</b> → ③ 새로 생긴 <b>🧭 아이콘</b>으로 열기</span>');
      return;
    }
    if (Notification.permission === 'denied') {
      setState(box, 'off', '<span class="pl">알림</span><span class="pd">브라우저에서 알림이 차단돼 있습니다. 설정에서 허용해 주세요.</span>');
      return;
    }

    // 먼저 버튼을 그려 놓는다. 아래 조회는 '켜짐' 여부를 확인하는 보정일 뿐,
    // 그 결과를 기다렸다가 그리면 안 된다 — serviceWorker.ready 는 서비스워커가
    // 활성화되지 않으면 실패하지도 않고 영원히 대기한다(.catch 도 안 걸린다).
    // 그 사이 칸이 비어 있으면 :empty 규칙에 숨겨져 화면에서 사라진다.
    setState(box, '', '<span class="pl">앱 알림</span><span class="pd">매일 아침, 새 브리핑이 올라오면 알려드릴까요?</span>' +
      '<button class="pbtn" onclick="nbPushOn()">알림 받기</button>');

    navigator.serviceWorker.ready.then(function (reg) {
      return reg.pushManager.getSubscription();
    }).then(function (sub) {
      if (sub) {
        setState(box, 'on', '<span class="pl">알림 켜짐</span><span class="pd">매일 아침 새 브리핑을 알려드립니다.</span>' +
          '<button class="pbtn ghost" onclick="nbPushOff()">끄기</button>');
      }
    }).catch(function () {});
  };

  /* 서비스워커가 준비될 때까지 기다리되, 무한정은 아니다.
     ready 는 실패하지 않고 계속 매달려 있기만 하므로 직접 시한을 둔다. */
  function swReady(ms) {
    return Promise.race([
      navigator.serviceWorker.ready,
      new Promise(function (_, reject) {
        setTimeout(function () { reject(new Error('sw-timeout')); }, ms || 8000);
      }),
    ]).catch(function () {
      // 아직 등록 전일 수 있으니 한 번 직접 등록해 보고 다시 기다린다.
      // 여기서도 시한을 둔다 — 안 그러면 '설정하는 중…'에서 영원히 멈춘다.
      return Promise.race([
        navigator.serviceWorker.register('/sw.js').then(function () {
          return navigator.serviceWorker.ready;
        }),
        new Promise(function (_, reject) {
          setTimeout(function () { reject(new Error('서비스워커 준비 실패')); }, ms || 8000);
        }),
      ]);
    });
  }

  window.nbPushOn = function () {
    var box = document.getElementById('pushbox');
    setState(box, '', '<span class="pl">앱 알림</span><span class="pd">설정하는 중…</span>');
    Notification.requestPermission().then(function (p) {
      if (p !== 'granted') { window.nbPushInit(); return; }
      return swReady(8000).then(function (reg) {
        return reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: b64ToU8(VAPID_PUBLIC),
        });
      }).then(function (sub) {
        return fetch(API, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ subscription: sub }),
        });
      }).then(function () {
        setState(box, 'on', '<span class="pl">알림 켜짐</span><span class="pd">내일 아침부터 알려드릴게요.</span>' +
          '<button class="pbtn ghost" onclick="nbPushOff()">끄기</button>');
      });
    }).catch(function (e) {
      // 실패 사유를 화면에 남긴다 — 안 그러면 원인을 물어봐야만 알 수 있다
      var why = (e && (e.name || e.message)) ? ' (' + (e.name || e.message) + ')' : '';
      setState(box, 'off', '<span class="pl">알림</span><span class="pd">알림 설정에 실패했습니다' + why +
        '. 다시 시도해 주세요.</span><button class="pbtn" onclick="nbPushOn()">다시 시도</button>');
    });
  };

  window.nbPushOff = function () {
    navigator.serviceWorker.ready.then(function (reg) {
      return reg.pushManager.getSubscription();
    }).then(function (sub) {
      if (!sub) return;
      var ep = sub.endpoint;
      return sub.unsubscribe().then(function () {
        return fetch(API, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ subscription: { endpoint: ep } }),
        });
      });
    }).then(function () { window.nbPushInit(); }).catch(function () {});
  };
})();
