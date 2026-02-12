// 요청만 담당
// recommendByImage(file, limit, textQuery) 함수 하나
// FormData 만들고 fetch → JSON 반환

export async function recommendByImage(
  file,
  limit = 8,
  textQuery = "",
  category = "",
  gender = "",
  guestId = "",
  nickname = "",
  style = "",
) {
  if (!file) {
    return { error: { code: "NO_FILE", message: "이미지를 업로드해주세요" } };
  }
  const form = new FormData();

  // 1) 이미지 파일
  form.append("image", file);

  // 2) 숫자/문자도 FormData에 넣을 수 있음 (자동으로 문자열로 들어감)
  form.append("limit", String(limit ?? 8));

  // 3) 텍스트도 같이 전송 (스프링에서 @RequestParam("textQuery")로 받기)
  //    빈 문자열이면 백엔드에서 무시하거나, q 튜닝에 쓰면 됨
  form.append("textQuery", textQuery ?? "");
  // + 카테고리, 성별도 추가로 보내기
  form.append("category", category ?? "");
  form.append("gender", gender ?? "");
  form.append("guestId", guestId ?? "");
  form.append("nickname", nickname ?? "");
  form.append("style", style ?? "");

  const res = await fetch("/api/v1/recommend/image", {
    method: "POST",
    body: form,
  });

  const raw = await res.text();
  let data = null;
  try {
    data = raw ? JSON.parse(raw) : null;
  } catch {}

  if (!res.ok) {
    console.error("[recommendByImage] HTTP", res.status, data ?? raw);
    if (data?.error) return data;
    return {
      error: {
        code: `HTTP_${res.status}`,
        message: raw || "서버 오류가 발생했어",
      },
    };
  }

  return data;
}
