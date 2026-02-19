// src/components/stage/AIMessage.jsx
import React from "react";

const TypingDots = () => {
  return (
    <div className="flex items-center gap-1">
      <span className="w-2 h-2 rounded-full bg-foreground/60 animate-bounce [animation-delay:-0.3s]" />
      <span className="w-2 h-2 rounded-full bg-foreground/60 animate-bounce [animation-delay:-0.15s]" />
      <span className="w-2 h-2 rounded-full bg-foreground/60 animate-bounce" />
    </div>
  );
};

function renderFormattedText(text) {
  const lines = String(text ?? "").split("\n");

  return (
    <div className="space-y-2">
      {lines.map((line, i) => {
        const trimmed = line.trim();

        if (!trimmed) return <div key={i} className="h-2" />;

        if (trimmed.startsWith("### ")) {
          return (
            <h3
              key={i}
              className="text-md md:text-base font-semibold leading-snug"
            >
              {trimmed.replace("### ", "")}
            </h3>
          );
        }

        if (trimmed.startsWith("## ")) {
          return (
            <h2
              key={i}
              className="text-base md:text-lg font-semibold leading-snug"
            >
              {trimmed.replace("## ", "")}
            </h2>
          );
        }

        return (
          <p
            key={i}
            className="text-md md:text-base leading-relaxed whitespace-pre-wrap break-words"
          >
            {trimmed}
          </p>
        );
      })}
    </div>
  );
}

const AIMessage = ({
  content = "",
  role = "assistant",
  variant = "default",
}) => {
  const text = String(content ?? "").trim();

  const isTyping = role === "assistant" && variant !== "error" && text === "…";
  if (!text && !isTyping) return null;

  const isUser = role === "user";
  const isError = variant === "error";

  const align = isUser ? "ml-auto md:mr-4" : "mr-auto md:ml-4";

  const tone = isError
    ? "bg-red-50 text-red-700 border border-red-200"
    : isUser
      ? "bg-muted text-foreground"
      : "bg-muted/60 text-foreground";

  return (
    <div
      className={[
        align,
        "mt-3 w-fit rounded-2xl shadow break-words",
        "px-3 py-2 md:px-4 md:py-3",
        "text-md md:text-base",
        "max-w-[300px] md:max-w-[420px]",
        tone,
      ].join(" ")}
    >
      {isTyping ? (
        <TypingDots />
      ) : role === "assistant" ? (
        renderFormattedText(text)
      ) : (
        <div className="whitespace-pre-wrap leading-relaxed">{text}</div>
      )}
    </div>
  );
};

export default AIMessage;
