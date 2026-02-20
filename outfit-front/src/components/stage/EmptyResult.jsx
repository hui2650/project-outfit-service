// src/components/stage/EmptyResult.jsx
import React from 'react'
import { useAppData } from '../../store/appDataStore'
import useTypewriter from '../../hooks/useTypewriter'

/**
 *  EmptyResult (처음 진입 화면)
 * - 채팅 로그가 0개일 때 보여주는 온보딩/가이드 뷰
 * - guest.nickname을 끌어와서 개인화된 인사말을 타이핑 효과로 보여줌
 * - 프로젝트 컨셉: 게스트 로그인/닉네임 기반이라 이 개인화가 UX 포인트
 */

const EmptyResult = () => {
  const { guest } = useAppData()
  const nickname = guest?.nickname?.trim() || '게스트 사용자'

  // 기본멘트 (타이핑효과) 닉네임 포함해서 인사 -> 서비스 시작 유도
  const fullText = `${nickname}님, 안녕하세요.\nAI 코디 추천을 시작해보세요!`

  // 타이핑 효과 훅: linePause로 줄바꿈 멈춤도 줘서 자연스럽게
  const { out, done } = useTypewriter(fullText, {
    speed: 65,
    startDelay: 120,
    linePause: 300,
  })

  return (
    <div className="flex h-full w-full items-center justify-center px-4">
      <div className="text-center max-w-md">
        {/* 타이핑 되는 헤드라인 */}
        <h2
          className="
          text-2xl md:text-3xl
          text-foreground/95 font-medium mb-5
          whitespace-pre-line leading-snug
        "
        >
          {out}
          {/* 커서 효과: 타이핑 중엔 깜빡, 끝나면 숨김 */}
          <span
            className={[
              'inline-block align-baseline ml-0.5',
              'w-[0.6ch] h-[1em]',
              'border-r-2 border-current',
              done ? 'opacity-0' : 'animate-blink',
            ].join(' ')}
            aria-hidden="true"
          />
        </h2>

        {/* 타이핑 완료 후 안내문이 서서히 나타나게 */}
        <p
          className={[
            'text-sm md:text-base',
            'text-muted-foreground leading-relaxed',
            'transition-opacity duration-500 delay-150',
            done ? 'opacity-100' : 'opacity-0',
          ].join(' ')}
        >
          오른쪽에서 아이템 이미지를 업로드하고
          <br />
          카테고리와 성별을 선택하면
          <br />
          AI가 어울리는 코디를 추천해드려요.
        </p>
      </div>
    </div>
  )
}

export default EmptyResult
