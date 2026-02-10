import React from "react";
import { useAppData } from "../store/appDataStore.jsx";
import Header from "../components/layout/Header.jsx";

const UserPage = () => {
  const { favorites, history } = useAppData();

  return (
    <>
      <Header />
      <div className="min-h-screen p-6">
        <h2 className="text-2xl font-bold">내 기록</h2>

        <section className="mt-8">
          <h3 className="text-lg font-semibold">좋아요</h3>
          <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-4">
            {favorites.map((it) => (
              <img
                key={it.itemKey}
                src={it.imageUrl}
                alt={it.title}
                className="w-full h-48 object-cover rounded-xl"
              />
            ))}
          </div>
        </section>

        <section className="mt-10">
          <h3 className="text-lg font-semibold">히스토리(요청 단위)</h3>
          <div className="mt-3 space-y-4">
            {history.map((h) => (
              <div
                key={h.requestId ?? h.turnId}
                className="rounded-xl border p-4"
              >
                <div className="text-sm text-muted-foreground">
                  {new Date(h.createdAt).toLocaleString()}
                  {" · "}
                  {h.input?.category} / {h.input?.gender}
                </div>
                <div className="mt-3 grid grid-cols-4 gap-3">
                  {(h.items ?? []).slice(0, 4).map((it) => (
                    <img
                      key={it.itemKey}
                      src={it.imageUrl}
                      alt={it.title}
                      className="w-full h-24 object-cover rounded-lg"
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </>
  );
};

export default UserPage;
