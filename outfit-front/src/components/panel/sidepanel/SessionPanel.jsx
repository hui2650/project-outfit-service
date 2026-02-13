import React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faTrashCan, faPen } from "@fortawesome/free-solid-svg-icons";
import SidePanelHeader from "../sidepanel/SidePanelHeader";
import SidePanelFooter from "../sidepanel/SidePanelFooter";
import PanelShell from "../../layout/PanelShell.jsx";
import { useLayout } from "../../../store/layoutStore.jsx";
import { useAppData } from "../../../store/appDataStore.jsx";
import { useChatPage } from "../../../pages/chat/ChatPageContext.jsx";
import ConfirmModal from "../../common/ConfirmModal.jsx";

const SessionPanel = () => {
  const {
    chatSessions,
    currentSessionId,
    selectSession,
    renameSession, // 추가
    deleteSession, // 추가
  } = useAppData();

  const { setPanelCollapsed } = useLayout();
  const { openInputPanel, openSessionsPanel } = useChatPage();

  const [editingId, setEditingId] = React.useState(null);
  const [draftTitle, setDraftTitle] = React.useState("");
  const [deleteTarget, setDeleteTarget] = React.useState(null);

  const startEdit = (s) => {
    setEditingId(s.sessionId);
    setDraftTitle(s.title ?? "");
  };

  const commitEdit = (sessionId) => {
    renameSession(sessionId, draftTitle);
    setEditingId(null);
    setDraftTitle("");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setDraftTitle("");
  };

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
                  openInputPanel?.();
                  setPanelCollapsed(false); // ✅ 모바일/접힘 상태면 펼치기
                }}
                className="mt-4 w-full rounded-xl bg-primary/90 text-primary-foreground px-4 py-3 text-sm font-semibold hover:opacity-90 transition"
              >
                아이템 입력하러 가기
              </button>
            </div>
          </div>
        ) : (
          chatSessions.map((s) => {
            const active = s.sessionId === currentSessionId;
            const isEditing = editingId === s.sessionId;

            return (
              <div
                key={s.sessionId}
                className={[
                  "w-full rounded-xl border p-3 transition flex justify-between items-center",
                  active ? "bg-foreground/10" : "hover:bg-foreground/20",
                ].join(" ")}
              >
                <button
                  type="button"
                  onClick={() => {
                    selectSession(s.sessionId);
                    openInputPanel();
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
                              if (e.key === "Enter") commitEdit(s.sessionId);
                              if (e.key === "Escape") cancelEdit();
                            }}
                            onBlur={() => commitEdit(s.sessionId)}
                          />
                        ) : (
                          <>
                            <span className="truncate">
                              {s.title ?? "새 채팅"}
                            </span>

                            {/* title에 hover 했을 때만 노출 */}
                            <button
                              type="button"
                              className="opacity-0 group-hover/title:opacity-100 transition-opacity h-7 w-7 rounded-lg hover:bg-muted/30 flex items-center justify-center"
                              onClick={(e) => {
                                e.stopPropagation(); // 세션 선택 클릭 막기
                                startEdit(s);
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
                      {new Date(s.createdAt).toLocaleString()} ·{" "}
                    </div>
                  </div>
                </button>

                {/* 삭제 버튼 */}
                <button
                  type="button"
                  className="ml-2 h-8 w-8 rounded-lg hover:bg-muted/30 flex items-center justify-center"
                  onClick={(e) => {
                    e.stopPropagation();
                    setDeleteTarget(s);
                  }}
                  aria-label="채팅 삭제"
                  title="삭제"
                >
                  <FontAwesomeIcon icon={faTrashCan} />
                </button>
              </div>
            );
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
              ? `"${deleteTarget.title ?? "새 채팅"}"을(를) 삭제할까요?`
              : ""
          }
          confirmText="삭제"
          cancelText="취소"
          onConfirm={() => {
            if (!deleteTarget) return;
            deleteSession(deleteTarget.sessionId);
            setDeleteTarget(null);
          }}
          onClose={() => setDeleteTarget(null)}
          bgColor={"bg-destructive"}
        />
      )}
    </PanelShell>
  );
};

export default SessionPanel;
