// ZERODA PWA Service Worker v1.0
const CACHE_NAME = 'zeroda-driver-v1';
const OFFLINE_URL = '/static/offline.html';

// 캐시할 정적 리소스
const PRECACHE_URLS = [
  OFFLINE_URL,
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/manifest.json'
];

// 설치: 정적 리소스 사전 캐시
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_URLS);
    })
  );
  self.skipWaiting();
});

// 활성화: 이전 버전 캐시 정리
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// 네트워크 우선 전략 (Network First)
// Streamlit은 실시간 WebSocket 기반이므로 오프라인 완전 지원은 불가
// 네트워크 실패 시 오프라인 안내 페이지 표시
self.addEventListener('fetch', (event) => {
  // WebSocket, Streamlit 내부 요청은 통과
  if (event.request.url.includes('_stcore') ||
      event.request.url.includes('stream') ||
      event.request.mode === 'websocket') {
    return;
  }

  // 정적 리소스는 캐시 우선
  if (event.request.url.includes('/static/')) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        return cached || fetch(event.request).then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return response;
        });
      })
    );
    return;
  }

  // 기타 요청: 네트워크 우선, 실패 시 오프라인 페이지
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match(OFFLINE_URL);
      })
    );
  }
});
