// 요청만 담당
// recommendByImage(file, limit, textQuery) 함수 하나
// FormData 만들고 fetch → JSON 반환

export async function recommendByImage(file, limit = 8, textQuery = "") {
  const form = new FormData();

  // 1) 이미지 파일
  form.append("image", file);

  // 2) 숫자/문자도 FormData에 넣을 수 있음 (자동으로 문자열로 들어감)
  form.append("limit", String(limit));

  // 3) 텍스트도 같이 전송 (스프링에서 @RequestParam("textQuery")로 받기)
  //    빈 문자열이면 백엔드에서 무시하거나, q 튜닝에 쓰면 됨
  form.append("textQuery", textQuery);

  const res = await fetch("/api/v1/recommend/image", {
    method: "POST",
    body: form,
  });

  // 서버가 4xx/5xx면 여기서 throw해서 catch로 보내는게 UX 깔끔함
  // (서버가 항상 JSON으로 에러를 주더라도, status 체크는 해두는 편이 안전)
  const data = await res.json().catch(() => null);

  if (!res.ok) {
    // 서버가 준 JSON 에러 포맷이 있으면 우선 사용
    if (data?.error) return data;
    throw new Error("HTTP_ERROR");
  }

  return data;
}
