// src/components/stage/ChatComposer.jsx
import React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPaperPlane } from "@fortawesome/free-solid-svg-icons";

export default function ChatComposer({ disabled = false, onSend }) {
  const [text, setText] = React.useState("");

  const submit = () => {
    const v = text.trim();
    if (!v || disabled) return;
    onSend?.(v);
    setText("");
  };

  return (
    <div className="sticky bottom-0 left-0 right-0 z-10 pointer-events-none">
      {/*  모바일: px-4 / md 이상 확장 */}
      <div className="pointer-events-auto w-full px-4 lg:px-8 pb-5 pt-3 md:pb-6 md:pt-4 bg-background">
        {/*  모바일: w-full / md 이상부터 max-width 제한 */}
        <div className="w-full md:mx-auto md:max-w-3xl rounded-2xl border border-border bg-card shadow-2xl px-3 py-2">
          <div className="flex items-center gap-2">
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit();
                }
              }}
              disabled={disabled}
              placeholder={
                disabled
                  ? "결과가 있을 때 질문 가능합니다."
                  : "질문을 입력하세요..."
              }
              className="flex-1 bg-transparent outline-none text-md md:text-base pl-2 placeholder:text-muted-foreground disabled:opacity-60"
            />

            <button
              type="button"
              onClick={submit}
              disabled={disabled || !text.trim()}
              className="h-10 md:h-11 px-4 rounded-xl bg-primary/90 text-primary-foreground hover:opacity-90 transition-all active:scale-95 disabled:opacity-50 flex items-center justify-center"
              aria-label="send"
              title="send"
            >
              <FontAwesomeIcon
                icon={faPaperPlane}
                className="text-base md:text-lg"
              />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
