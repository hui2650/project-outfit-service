import React from "react";
import { useAppData } from "../store/appDataStore.jsx";
import Header from "../components/layout/Header.jsx";
import FavoritesSection from "../components/user/FavoritesSection.jsx";
import HistorySection from "../components/user/HistorySection.jsx";
import ResultModal from "../components/common/ResultModal.jsx";

const UserPage = () => {
  const { favorites, history } = useAppData();

  const [isModalOpen, setIsModalOpen] = React.useState(false);
  const [modalItems, setModalItems] = React.useState([]);
  const [modalIndex, setModalIndex] = React.useState(0);

  const openModalWith = (items, index = 0) => {
    setModalItems(items ?? []);
    setModalIndex(index ?? 0);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setModalItems([]);
    setModalIndex(0);
  };

  return (
    <>
      <Header />

      <div className="min-h-screen p-6 mt-14">
        <h2 className="text-2xl font-bold">내 기록</h2>

        <FavoritesSection
          favorites={favorites ?? []}
          onClickItem={(item) => {
            const idx = (favorites ?? []).findIndex(
              (x) => x.itemKey === item.itemKey,
            );
            openModalWith(favorites ?? [], Math.max(idx, 0));
          }}
        />

        <HistorySection
          history={history ?? []}
          onClickHistory={(h) => {
            // 히스토리 클릭하면 그 요청의 결과 items를 모달로
            openModalWith(h.items ?? [], 0);
          }}
        />
      </div>

      {/* ✅ 핵심: 열릴 때만 렌더 */}
      {isModalOpen && (
        <ResultModal
          items={modalItems}
          index={modalIndex}
          onClose={closeModal}
          onChangeIndex={setModalIndex}
        />
      )}
    </>
  );
};

export default UserPage;
