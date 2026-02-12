import React from "react";

export default function ConfirmModal({
  open,
  title,
  message = "",
  confirmText = "이동",
  cancelText = "취소",
  onConfirm,
  onClose,
  bgColor,
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
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/40"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-modal-title"
    >
      <div className="w-[320px] rounded-2xl bg-card border border-border p-4">
        <div id="confirm-modal-title" className="font-semibold mb-2">
          {title}
        </div>

        {message ? (
          <div className="text-sm text-muted-foreground mb-4">{message}</div>
        ) : (
          <div className="mb-4" />
        )}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            className="px-3 py-2 rounded-lg bg-muted/70 hover:bg-muted"
            onClick={onClose}
          >
            {cancelText}
          </button>

          <button
            type="button"
            className={`${bgColor} px-3 py-2 rounded-lg  text-white`}
            onClick={onConfirm}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
