import React from "react";

export default function ConfirmModal({
  open,
  title = "이동할까?",
  message = "",
  confirmText = "이동",
  cancelText = "취소",
  onConfirm,
  onClose,
}) {
  // ESC 닫기
  React.useEffect(() => {
    if (!open) return;
    const onKeyDown = (e) => {
      if (e.key === "Escape") onClose?.();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  // 바디 스크롤 잠금
  React.useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[2000]">
      <div
        className="absolute inset-0 bg-foreground/60"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative h-full w-full flex items-center justify-center p-6">
        <div className="w-full max-w-md rounded-2xl bg-card shadow-xl border p-5">
          <div className="text-lg font-semibold text-card-foreground">
            {title}
          </div>
          {message ? (
            <div className="mt-2 text-sm text-muted-foreground leading-relaxed">
              {message}
            </div>
          ) : null}

          <div className="mt-5 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border bg-card hover:bg-secondary transition"
            >
              {cancelText}
            </button>
            <button
              type="button"
              onClick={() => {
                onConfirm?.();
                onClose?.();
              }}
              className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-95 transition"
            >
              {confirmText}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
