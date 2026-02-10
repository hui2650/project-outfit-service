// src/api/chat.js
export async function askFollowup({
  text,
  requestId = null,
  items = [],
  category = "",
  gender = "",
}) {
  const res = await fetch("/api/v1/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      requestId,
      items, // 추천 결과를 컨텍스트로 넘기고 싶으면
      category,
      gender,
    }),
  });

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    if (data?.error) return data;
    throw new Error("HTTP_ERROR");
  }

  return data; // 예: { answer: "..." } 또는 { error: {...} }
}
