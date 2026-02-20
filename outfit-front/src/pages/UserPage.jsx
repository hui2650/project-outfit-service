// src/pages/UserPage.jsx
import React from 'react'
import { useAppData } from '../store/appDataStore.jsx'
import Header from '../components/layout/Header.jsx'
import FavoritesSection from '../components/user/FavoritesSection.jsx'
import HistorySection from '../components/user/HistorySection.jsx'
import ResultModal from '../components/common/ResultModal.jsx'

/*
UserPage
- 저장된 좋아요(favorites)와 히스토리(history)를 보여주는 페이지
- 이미지 클릭 시 ResultModal을 열어 결과를 크게 탐색할 수 있도록 구성
*/
const UserPage = () => {
  const { favorites, history } = useAppData()

  const [isModalOpen, setIsModalOpen] = React.useState(false)
  const [modalItems, setModalItems] = React.useState([])
  const [modalIndex, setModalIndex] = React.useState(0)

  const openModalWith = (items, index = 0) => {
    setModalItems(items ?? [])
    setModalIndex(index ?? 0)
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setModalItems([])
    setModalIndex(0)
  }

  return (
    <>
      <Header />

      {/* Header가 fixed일 수 있으므로 상단 여백(mt-14) 확보 */}
      <div className="min-h-screen p-6 mt-14">
        <h2 className="text-2xl font-bold">내 기록</h2>

        <FavoritesSection
          favorites={favorites ?? []}
          onClickItem={(item) => {
            const idx = (favorites ?? []).findIndex(
              (x) => x.itemKey === item.itemKey
            )
            openModalWith(favorites ?? [], Math.max(idx, 0))
          }}
        />

        <HistorySection
          history={history ?? []}
          onClickHistory={(h) => {
            openModalWith(h.items ?? [], 0)
          }}
        />
      </div>

      {/* 모달은 열릴 때만 렌더링 */}
      {isModalOpen && (
        <ResultModal
          items={modalItems}
          index={modalIndex}
          onClose={closeModal}
          onChangeIndex={setModalIndex}
        />
      )}
    </>
  )
}

export default UserPage
