export async function askFollowup({
  text,
  requestId = null,
  items = [],
  category = "",
  gender = "",
  guestId = null,
  nickname = "",
  style = "",
}) {
  const res = await fetch("/api/v1/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      requestId,
      items,
      category,
      gender,
      guestId,
      nickname,
      style,
    }),
  });

  const rawBody = await res.text(); //  로그용
  const data = JSON.parse(rawBody); //  UI용 (answer 포함)

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
