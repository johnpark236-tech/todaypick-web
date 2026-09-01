// TodayPick 공유 이미지 하단 footer UI 설정
// 이 파일에서 font 크기·굵기·여백을 한 곳에서 조정할 수 있습니다.
// fontSize는 refWidth(800px) 기준 절대값. 실제 렌더링 시 canvas 폭에 비례해 자동 스케일됩니다.

// FUTURE_PLAN:
// Weather API integration planned.
// Do not display placeholder until actual API integration is implemented.

export const SHARE_UI = {
  footer: {
    refWidth: 800,

    label: {
      text: '오늘의 코디명:',
      fontSize: 30,       // px (at refWidth 800)
      fontWeight: 700,
      color: '#1A1A1A',
    },

    title: {
      fontSize: 34,       // px (at refWidth 800)
      fontWeight: 700,
      lineHeight: 1.45,
      maxLines: 2,
      color: '#1A1A1A',
    },

    spacing: {
      labelToTitle: 10,   // px gap between label and title (at refWidth 800)
      paddingTop: 24,     // px (at refWidth 800)
      paddingBottom: 28,  // px (at refWidth 800)
      paddingHoriz: 28,   // px from accent line to text (at refWidth 800)
    },

    accent: {
      color: '#C9A96E',
      widthRatio: 0.008,  // fraction of canvas width
    },

    background: '#FFFFFF',
    separator: '#E8E2D9',
  },

  watermark: {
    text: 'TodayPick',
    fontSizeRatio: 0.04,  // fraction of canvas width
    fontWeight: 700,
    color: 'rgba(255,255,255,0.92)',
    shadowColor: 'rgba(0,0,0,0.65)',
    shadowBlur: 5,
    padRatio: 0.04,       // fraction of canvas width
  },
};
