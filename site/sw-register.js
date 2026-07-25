/* 서비스워커 등록 + '홈 화면에 추가' 안내 배너 */
(function () {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/sw.js').catch(function () {});
    });
  }

  // 이미 앱으로 실행 중이면 안내 불필요
  var standalone = window.matchMedia('(display-mode: standalone)').matches ||
                   window.navigator.standalone === true;
  if (standalone || localStorage.getItem('nb-a2hs-hide') === '1') return;

  var isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  var deferred = null;

  function banner(html, onInstall) {
    var d = document.createElement('div');
    d.className = 'a2hs';
    d.innerHTML = '<div class="a2hs-in"><span class="a2hs-ico">🧭</span>' +
      '<span class="a2hs-tx">' + html + '</span>' +
      (onInstall ? '<button class="a2hs-go">설치</button>' : '') +
      '<button class="a2hs-x" aria-label="닫기">&times;</button></div>';
    document.body.appendChild(d);
    requestAnimationFrame(function () { d.classList.add('on'); });
    d.querySelector('.a2hs-x').onclick = function () {
      d.classList.remove('on');
      localStorage.setItem('nb-a2hs-hide', '1');
      setTimeout(function () { d.remove(); }, 300);
    };
    if (onInstall) d.querySelector('.a2hs-go').onclick = function () { onInstall(d); };
  }

  // Android / Chrome — 설치 버튼 제공
  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferred = e;
    banner('홈 화면에 추가하면 앱처럼 쓸 수 있어요', function (d) {
      deferred.prompt();
      deferred.userChoice.then(function () {
        d.classList.remove('on');
        localStorage.setItem('nb-a2hs-hide', '1');
        setTimeout(function () { d.remove(); }, 300);
      });
    });
  });

  // iOS — 수동 안내 (자동 설치 API가 없음)
  if (isIOS) {
    setTimeout(function () {
      banner('공유 <b>&#8679;</b> → <b>홈 화면에 추가</b> 하면 앱처럼 쓸 수 있어요', null);
    }, 2500);
  }
})();
