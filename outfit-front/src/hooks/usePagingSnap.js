import { useEffect, useRef } from "react";

/**
 * usePagingSnap(scrollerRef, options)
 *
 * - Wheel: delta 누적 임계값 넘으면 1칸 이동 (트랙패드 대응)
 * - Keyboard: ArrowUp/Down, PageUp/Down, Home/End, Space 지원
 * - Touch: 세로 스와이프 임계값 넘으면 1칸 이동
 *
 * options:
 *  selector: 섹션을 찾는 CSS selector (default: "[data-hero-section]")
 *  lockMs: 한 번 이동 후 입력 무시 시간 (default: 900)
 *  wheelThreshold: wheel delta 누적 임계값 (default: 40)
 *  wheelResetMs: wheel 누적 리셋 기준(이 시간보다 느리면 누적 0) (default: 180)
 *  swipeThresholdPx: 터치 스와이프 임계 px (default: 60)
 *  durationMs: smooth scroll 감각 안정용 (default: 650)
 */
export default function usePagingSnap(
  scrollerRef,
  {
    selector = "[data-hero-section]",
    lockMs = 900,
    wheelThreshold = 40,
    wheelResetMs = 180,
    swipeThresholdPx = 60,
    durationMs = 650,
  } = {},
) {
  const lockedRef = useRef(false);

  // wheel accumulate
  const wheelAccRef = useRef(0);
  const wheelLastTRef = useRef(0);

  // touch tracking
  const touchStartYRef = useRef(null);
  const touchMovedRef = useRef(false);

  const lock = () => {
    lockedRef.current = true;
    window.setTimeout(() => {
      lockedRef.current = false;
    }, lockMs);
  };

  useEffect(() => {
    const el = scrollerRef?.current;
    if (!el) return;

    const getSections = () =>
      Array.from(el.querySelectorAll(selector)).filter(Boolean);

    const getCurrentIndex = (sections) => {
      const st = el.scrollTop;
      let bestIdx = 0;
      let bestDist = Infinity;

      for (let i = 0; i < sections.length; i++) {
        const top = sections[i].offsetTop;
        const dist = Math.abs(top - st);
        if (dist < bestDist) {
          bestDist = dist;
          bestIdx = i;
        }
      }
      return bestIdx;
    };

    const snapToIndex = (idx) => {
      const sections = getSections();
      if (sections.length === 0) return;

      const clamped = Math.max(0, Math.min(sections.length - 1, idx));
      const target = sections[clamped];
      if (!target) return;

      lock();
      // 모든 누적/상태 리셋
      wheelAccRef.current = 0;
      touchStartYRef.current = null;
      touchMovedRef.current = false;

      target.scrollIntoView({ behavior: "smooth", block: "start" });

      // smooth 진행 동안 잔여 입력 안정화
      window.setTimeout(() => {
        wheelAccRef.current = 0;
      }, durationMs);
    };

    const snapByDelta = (dir) => {
      if (lockedRef.current) return;

      const sections = getSections();
      if (sections.length === 0) return;

      const cur = getCurrentIndex(sections);
      const next = Math.max(0, Math.min(sections.length - 1, cur + dir));

      if (next === cur) {
        // 끝에서 폭주 방지
        lock();
        wheelAccRef.current = 0;
        return;
      }
      snapToIndex(next);
    };

    // ------------------------
    // Wheel
    // ------------------------
    const onWheel = (e) => {
      e.preventDefault();
      if (lockedRef.current) return;

      const now = performance.now();
      const dt = now - (wheelLastTRef.current || now);
      wheelLastTRef.current = now;

      // 느리게 들어오면 누적 초기화
      if (dt > wheelResetMs) wheelAccRef.current = 0;

      const dy = e.deltaY;
      if (Math.abs(dy) < 2) return;

      wheelAccRef.current += dy;

      if (Math.abs(wheelAccRef.current) < wheelThreshold) return;

      const dir = wheelAccRef.current > 0 ? 1 : -1;
      snapByDelta(dir);
      wheelAccRef.current = 0;
    };

    // ------------------------
    // Keyboard
    // ------------------------
    const onKeyDown = (e) => {
      // input/textarea/contenteditable에서는 방해하지 않기
      const t = e.target;
      const isTypingTarget =
        t &&
        (t.tagName === "INPUT" ||
          t.tagName === "TEXTAREA" ||
          t.isContentEditable);

      if (isTypingTarget) return;
      if (lockedRef.current) return;

      const key = e.key;

      // Space: 아래로 (Shift+Space: 위로)
      if (key === " " || key === "Spacebar") {
        e.preventDefault();
        snapByDelta(e.shiftKey ? -1 : 1);
        return;
      }

      if (key === "ArrowDown" || key === "PageDown") {
        e.preventDefault();
        snapByDelta(1);
        return;
      }

      if (key === "ArrowUp" || key === "PageUp") {
        e.preventDefault();
        snapByDelta(-1);
        return;
      }

      if (key === "Home") {
        e.preventDefault();
        snapToIndex(0);
        return;
      }

      if (key === "End") {
        e.preventDefault();
        const sections = getSections();
        snapToIndex(sections.length - 1);
        return;
      }
    };

    // ------------------------
    // Touch
    // ------------------------
    const onTouchStart = (e) => {
      if (lockedRef.current) return;
      if (e.touches && e.touches.length === 1) {
        touchStartYRef.current = e.touches[0].clientY;
        touchMovedRef.current = false;
      }
    };

    const onTouchMove = (e) => {
      if (lockedRef.current) return;
      if (touchStartYRef.current == null) return;
      if (!e.touches || e.touches.length !== 1) return;

      const y = e.touches[0].clientY;
      const dy = y - touchStartYRef.current;

      // 스와이프가 감지되면 브라우저 기본 스크롤 막아서 “한 페이지 스냅”으로 통일
      if (Math.abs(dy) > 6) {
        touchMovedRef.current = true;
        e.preventDefault();
      }
    };

    const onTouchEnd = (e) => {
      if (lockedRef.current) return;
      const startY = touchStartYRef.current;
      touchStartYRef.current = null;

      if (!touchMovedRef.current || startY == null) return;

      // 터치 end에서는 changedTouches 사용
      const endY = (e.changedTouches && e.changedTouches[0]?.clientY) ?? null;
      if (endY == null) return;

      const dy = endY - startY;

      if (Math.abs(dy) < swipeThresholdPx) return;

      // 손가락이 위로 올라가면 화면은 아래로 이동(다음 섹션)
      const dir = dy < 0 ? 1 : -1;
      snapByDelta(dir);
    };

    // 이벤트 바인딩
    el.addEventListener("wheel", onWheel, { passive: false });
    // 키보드는 window에 걸어야 포커스가 컨테이너 밖이어도 먹음
    window.addEventListener("keydown", onKeyDown, { passive: false });

    // 터치는 컨테이너에
    el.addEventListener("touchstart", onTouchStart, { passive: true });
    el.addEventListener("touchmove", onTouchMove, { passive: false });
    el.addEventListener("touchend", onTouchEnd, { passive: true });

    return () => {
      el.removeEventListener("wheel", onWheel);
      window.removeEventListener("keydown", onKeyDown);

      el.removeEventListener("touchstart", onTouchStart);
      el.removeEventListener("touchmove", onTouchMove);
      el.removeEventListener("touchend", onTouchEnd);
    };
  }, [
    scrollerRef,
    selector,
    lockMs,
    wheelThreshold,
    wheelResetMs,
    swipeThresholdPx,
    durationMs,
  ]);
}
