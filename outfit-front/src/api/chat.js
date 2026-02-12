function isPlaceholderText(s) {
  const t = (s ?? "").trim();
  return !t || t === "…" || t === "..." || t.toLowerCase() === "loading";
}

function getLastAssistantText(chatLogs = []) {
  for (let i = chatLogs.length - 1; i >= 0; i--) {
    const m = chatLogs[i];
    if (!m) continue;

    // 케이스1: role 기반
    if (m.role === "assistant" && typeof m.content === "string") {
      const c = m.content.trim();
      if (c && !isPlaceholderText(c)) return c;
    }

    // 케이스2: type 기반
    if (
      (m.type === "bot" || m.sender === "assistant") &&
      typeof m.text === "string"
    ) {
      const t = m.text.trim();
      if (t && !isPlaceholderText(t)) return t;
    }

    // 케이스3: answer 기반
    if (m.role === "assistant" && typeof m.answer === "string") {
      const a = m.answer.trim();
      if (a && !isPlaceholderText(a)) return a;
    }
  }
  return "";
}

export async function askFollowup({
  text,
  requestId = null,
  items = [],
  category = "",
  gender = "",
  guestId = null,
  nickname = "",
  style = "",
  chatLogs = [],
}) {
  const prevAnswerRaw = getLastAssistantText(chatLogs);
  const prevAnswer = prevAnswerRaw.slice(0, 800); // 800자 정도만

  const payload = {
    text,
    requestId,
    items,
    category,
    gender,
    guestId,
    nickname,
    style,
    prevAnswer,
  };

  console.log("[chat] payload:", payload);
  const res = await fetch("/api/v1/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const rawBody = await res.text(); //  로그용
  let data;
  try {
    data = rawBody ? JSON.parse(rawBody) : {};
  } catch {
    data = { error: { message: rawBody || "Invalid JSON", code: "BAD_JSON" } };
  }

  console.log("[chat] status:", res.status);
  console.log("[chat] data:", data);
  // 필요하면 raw도 찍기
  console.log("[chat] rawBody:", rawBody);

  if (!res.ok) {
    if (data?.error) return data;
    throw new Error("HTTP_ERROR");
  }

  return data; //  { answer, requestId }
}
