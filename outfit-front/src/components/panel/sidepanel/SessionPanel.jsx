import React from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faTrashCan, faPen } from '@fortawesome/free-solid-svg-icons'
import SidePanelHeader from '../sidepanel/SidePanelHeader'
import SidePanelFooter from '../sidepanel/SidePanelFooter'
import PanelShell from '../../layout/PanelShell.jsx'
import { useLayout } from '../../../store/layoutStore.jsx'
import { useAppData } from '../../../store/appDataStore.jsx'
import { useChatPage } from '../../../pages/chat/ChatPageContext.jsx'
import ConfirmModal from '../../common/ConfirmModal.jsx'

/*
SessionPanel
- 이전 채팅(세션) 목록을 보여주는 패널
- appDataStore의 chatSessions/currentSessionId를 기반으로 렌더링
- 세션 선택(selectSession), 이름 변경(renameSession), 삭제(deleteSession) 제공
- 패널 헤더 토글 버튼으로 입력 패널로 전환 가능
*/

const SessionPanel = () => {
  const {
    chatSessions,
    currentSessionId,
    selectSession,
    renameSession,
    deleteSession,
  } = useAppData()

  const { setPanelCollapsed } = useLayout()
  const { openInputPanel, openSessionsPanel } = useChatPage()

  // 편집 상태: 특정 세션만 인라인 편집
  const [editingId, setEditingId] = React.useState(null)
  const [draftTitle, setDraftTitle] = React.useState('')

  // 삭제 확인 모달 대상
  const [deleteTarget, setDeleteTarget] = React.useState(null)

  const startEdit = (s) => {
    setEditingId(s.sessionId)
    setDraftTitle(s.title ?? '')
  }

  const commitEdit = (sessionId) => {
    renameSession(sessionId, draftTitle)
    setEditingId(null)
    setDraftTitle('')
  }

  const cancelEdit = () => {
    setEditingId(null)
    setDraftTitle('')
  }

  return (
    <PanelShell
      rail={{ onOpenInput: openInputPanel, onOpenSessions: openSessionsPanel }}
      header={
        <SidePanelHeader
          title="이전 채팅"
          onCollapse={() => setPanelCollapsed(true)}
          onToggleMode={openInputPanel}
          isSessionMode={true}
        />
      }
      footer={<SidePanelFooter />}
    >
      <div className="h-full p-4 space-y-2 overflow-y-auto scrollbar-nice">
        {(chatSessions?.length ?? 0) === 0 ? (
          /*
          빈 상태
          - 세션이 없을 때 안내 카드 표시
          - 버튼으로 입력 패널로 전환하고, 필요 시 collapsed를 해제해 패널을 펼침
          */
          <div className="h-full flex items-center justify-center">
            <div className="w-full max-w-[320px] rounded-2xl border border-border bg-card/60 px-5 py-6 text-center">
              <div className="text-base font-semibold text-foreground">
                아직 채팅이 없습니다.
              </div>
              <div className="mt-2 text-sm text-muted-foreground leading-relaxed">
                아이템을 입력해서 새 채팅을 시작해보세요!
              </div>

              {/* 선택: 입력 패널로 이동 버튼 */}
              <button
                type="button"
                onClick={() => {
                  openInputPanel?.()
                  setPanelCollapsed(false) // ✅ 모바일/접힘 상태면 펼치기
                }}
                className="mt-4 w-full rounded-xl bg-primary/90 text-primary-foreground px-4 py-3 text-sm font-semibold hover:opacity-90 transition"
              >
                아이템 입력하러 가기
              </button>
            </div>
          </div>
        ) : (
          /*
          세션 목록
          - active 세션은 배경을 다르게 표시
          - 제목은 인라인 편집 가능(Enter 저장, Escape 취소, blur 저장)
          - 삭제는 ConfirmModal로 보호
          */
          chatSessions.map((s) => {
            const active = s.sessionId === currentSessionId
            const isEditing = editingId === s.sessionId

            return (
              <div
                key={s.sessionId}
                className={[
                  'w-full rounded-xl border p-3 transition flex justify-between items-center',
                  active ? 'bg-foreground/10' : 'hover:bg-foreground/20',
                ].join(' ')}
              >
                <button
                  type="button"
                  onClick={() => {
                    selectSession(s.sessionId)
                    openInputPanel()
                  }}
                  className="flex-1 text-left"
                >
                  <div className="flex flex-col">
                    <div className="font-semibold text-sm">
                      <div className="group/title inline-flex items-center gap-2">
                        {isEditing ? (
                          <input
                            value={draftTitle}
                            onChange={(e) => setDraftTitle(e.target.value)}
                            className="w-full bg-transparent outline-none text-sm font-semibold"
                            autoFocus
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') commitEdit(s.sessionId)
                              if (e.key === 'Escape') cancelEdit()
                            }}
                            onBlur={() => commitEdit(s.sessionId)}
                          />
                        ) : (
                          <>
                            <span className="truncate">
                              {s.title ?? '새 채팅'}
                            </span>

                            {/* title에 hover 했을 때만 수정 아이콘 노출 */}
                            <button
                              type="button"
                              className="opacity-0 group-hover/title:opacity-100 transition-opacity h-7 w-7 rounded-lg hover:bg-muted/30 flex items-center justify-center"
                              onClick={(e) => {
                                e.stopPropagation() // 세션 선택 클릭 막기
                                startEdit(s)
                              }}
                              aria-label="채팅 이름 수정"
                              title="이름 수정"
                            >
                              <FontAwesomeIcon
                                icon={faPen}
                                className="text-xs"
                              />
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {new Date(s.createdAt).toLocaleString()} ·{' '}
                    </div>
                  </div>
                </button>

                {/* 삭제 버튼: 실제 삭제는 모달 confirm에서 수행 */}
                <button
                  type="button"
                  className="ml-2 h-8 w-8 rounded-lg hover:bg-muted/30 flex items-center justify-center"
                  onClick={(e) => {
                    e.stopPropagation()
                    setDeleteTarget(s)
                  }}
                  aria-label="채팅 삭제"
                  title="삭제"
                >
                  <FontAwesomeIcon icon={faTrashCan} />
                </button>
              </div>
            )
          })
        )}
      </div>

      {/* 삭제 확인 모달*/}
      {deleteTarget && (
        <ConfirmModal
          open={Boolean(deleteTarget)}
          title="채팅 삭제"
          message={
            deleteTarget
              ? `"${deleteTarget.title ?? '새 채팅'}"을(를) 삭제할까요?`
              : ''
          }
          confirmText="삭제"
          cancelText="취소"
          onConfirm={() => {
            if (!deleteTarget) return
            deleteSession(deleteTarget.sessionId)
            setDeleteTarget(null)
          }}
          onClose={() => setDeleteTarget(null)}
          bgColor={'bg-destructive'}
        />
      )}
    </PanelShell>
  )
}

export default SessionPanel
