// Outfit catalog service with accurate clothing remapping and 12 demographic groups (10s to 60s for female & male)
// Retains backward compatibility while expanding across 12 age-gender cohorts.

const FEMALE_LOOKS = [
  {
    "id": "LOOK000001",
    "title": "여성 버건디 슬림 니트 & 베이지 스커트 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "버건디 반팔 슬림 하이넥 니트",
        "price": 19800,
        "searchKeyword": "여성 버건디 반팔 슬림 골지 니트"
      },
      {
        "slot": "하의",
        "name": "베이지 A라인 플리츠 미니스커트",
        "price": 24500,
        "searchKeyword": "여성 베이지 A라인 플리츠 미니스커트"
      },
      {
        "slot": "신발",
        "name": "브라운 클래식 로퍼",
        "price": 34000,
        "searchKeyword": "여성 브라운 클래식 페니 로퍼"
      }
    ]
  },
  {
    "id": "LOOK000002",
    "title": "여성 아이보리 퍼프 블라우스 & 블랙 슬랙스 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "아이보리 퍼프소매 스모크 블라우스",
        "price": 23000,
        "searchKeyword": "여성 아이보리 퍼프소매 스모크 블라우스"
      },
      {
        "slot": "하의",
        "name": "블랙 하이웨스트 와이드 슬랙스",
        "price": 28000,
        "searchKeyword": "여성 블랙 하이웨스트 와이드 슬랙스"
      },
      {
        "slot": "신발",
        "name": "블랙 포인티드 토 플랫슈즈",
        "price": 31000,
        "searchKeyword": "여성 블랙 포인티드 플랫슈즈"
      }
    ]
  },
  {
    "id": "LOOK000003",
    "title": "여성 파스텔 핑크 반팔 니트 & 플리츠 스커트 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "라이트핑크 라운드넥 반팔 니트",
        "price": 21000,
        "searchKeyword": "여성 핑크 라운드넥 반팔 니트"
      },
      {
        "slot": "하의",
        "name": "아이보리 플리츠 미니스커트",
        "price": 25000,
        "searchKeyword": "여성 아이보리 플리츠 테니스 스커트"
      },
      {
        "slot": "신발",
        "name": "화이트 클래식 스니커즈",
        "price": 35000,
        "searchKeyword": "여성 화이트 로우탑 단화 스니커즈"
      }
    ]
  },
  {
    "id": "LOOK000004",
    "title": "여성 세이지그린 크롭 가디건 & 연청 와이드 데님 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "세이지그린 브이넥 크롭 니트 가디건",
        "price": 24000,
        "searchKeyword": "여성 민트 세이지그린 브이넥 크롭 니트 가디건"
      },
      {
        "slot": "하의",
        "name": "연청 하이웨스트 와이드 데님 팬츠",
        "price": 31000,
        "searchKeyword": "여성 연청 하이웨스트 와이드 데님 팬츠"
      },
      {
        "slot": "신발",
        "name": "크림 화이트 캔버스화",
        "price": 29000,
        "searchKeyword": "여성 크림 화이트 로우탑 캔버스화"
      }
    ]
  },
  {
    "id": "LOOK000005",
    "title": "여성 블랙 슬림 민소매 미니 원피스 룩",
    "outfitType": "one_piece",
    "items": [
      {
        "slot": "원피스",
        "name": "블랙 슬림핏 민소매 미니 원피스",
        "price": 32000,
        "searchKeyword": "여성 블랙 슬림핏 민소매 미니 원피스"
      },
      {
        "slot": "신발",
        "name": "블랙 미니멀 스트랩 샌들 힐",
        "price": 36000,
        "searchKeyword": "여성 블랙 스트랩 미들힐 샌들"
      }
    ]
  },
  {
    "id": "LOOK000006",
    "title": "여성 라이트그레이 가디건 & 화이트 롱스커트 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "라이트그레이 루즈핏 브이넥 니트",
        "price": 22000,
        "searchKeyword": "여성 라이트그레이 루즈핏 브이넥 니트"
      },
      {
        "slot": "하의",
        "name": "화이트 플리츠 A라인 롱스커트",
        "price": 29000,
        "searchKeyword": "여성 화이트 플리츠 A라인 롱스커트"
      },
      {
        "slot": "신발",
        "name": "아이보리 블록힐 펌프스",
        "price": 38000,
        "searchKeyword": "여성 아이보리 미들힐 펌프스 구두"
      }
    ]
  },
  {
    "id": "LOOK000007",
    "title": "여성 카멜 레더 재킷 & 화이트 이너 캐주얼 룩",
    "outfitType": "outer_set",
    "items": [
      {
        "slot": "아우터",
        "name": "카멜 브라운 오버핏 비건 레더 재킷",
        "price": 54000,
        "searchKeyword": "여성 카멜 브라운 크롭 가죽 레더 재킷"
      },
      {
        "slot": "상의",
        "name": "화이트 슬림 반팔 티셔츠",
        "price": 14000,
        "searchKeyword": "여성 화이트 라운드넥 슬림 크롭 반팔티"
      },
      {
        "slot": "하의",
        "name": "베이지 코튼 핀턱 미니스커트",
        "price": 23000,
        "searchKeyword": "여성 베이지 핀턱 A라인 면 미니스커트"
      },
      {
        "slot": "신발",
        "name": "브라운 미니멀 첼시 부츠",
        "price": 46000,
        "searchKeyword": "여성 브라운 앵클 첼시 부츠"
      }
    ]
  },
  {
    "id": "LOOK000008",
    "title": "여성 코랄 핑크 셔츠 플리츠 미니 원피스 룩",
    "outfitType": "one_piece",
    "items": [
      {
        "slot": "원피스",
        "name": "코랄 핑크 카라 셔츠 플리츠 미니 원피스",
        "price": 38000,
        "searchKeyword": "여성 핑크 카라 반팔 플리츠 미니 원피스"
      },
      {
        "slot": "신발",
        "name": "화이트 레이스업 플랫 단화",
        "price": 32000,
        "searchKeyword": "여성 화이트 레이스업 단화 플랫슈즈"
      }
    ]
  },
  {
    "id": "LOOK000009",
    "title": "여성 베이지 브이넥 니트 & 네이비 플리츠 스커트 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "오트밀 베이지 소프트 브이넥 니트",
        "price": 24000,
        "searchKeyword": "여성 오트밀 베이지 소프트 브이넥 니트"
      },
      {
        "slot": "하의",
        "name": "다크네이비 아코디언 플리츠 스커트",
        "price": 27000,
        "searchKeyword": "여성 네이비 아코디언 플리츠 미디스커트"
      },
      {
        "slot": "신발",
        "name": "블랙 에나멜 메리제인 슈즈",
        "price": 36000,
        "searchKeyword": "여성 블랙 에나멜 메리제인 플랫슈즈"
      }
    ]
  },
  {
    "id": "LOOK000010",
    "title": "여성 화이트 스모크 블라우스 & 베이지 롱스커트 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "화이트 스퀘어넥 퍼프소매 블라우스",
        "price": 25000,
        "searchKeyword": "여성 화이트 스퀘어넥 퍼프소매 블라우스"
      },
      {
        "slot": "하의",
        "name": "베이지 머메이드 라인 롱스커트",
        "price": 29000,
        "searchKeyword": "여성 베이지 하이웨스트 머메이드 롱스커트"
      },
      {
        "slot": "신발",
        "name": "누드 베이지 스트랩 샌들",
        "price": 33000,
        "searchKeyword": "여성 스킨 베이지 스트랩 미들힐 샌들"
      }
    ]
  },
  {
    "id": "LOOK000011",
    "title": "여성 테라코타 린넨 셔츠 & 크림 버뮤다 쇼츠 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "테라코타 오렌지 루즈핏 린넨 반팔 셔츠",
        "price": 26000,
        "searchKeyword": "여성 오렌지 브릭 린넨 반팔 셔츠"
      },
      {
        "slot": "하의",
        "name": "크림 아이보리 코튼 핀턱 쇼츠",
        "price": 22000,
        "searchKeyword": "여성 크림 아이보리 핀턱 코튼 반바지 쇼츠"
      },
      {
        "slot": "신발",
        "name": "카멜 브라운 스트랩 가죽 샌들",
        "price": 34000,
        "searchKeyword": "여성 브라운 스트랩 가죽 플랫 샌들"
      }
    ]
  },
  {
    "id": "LOOK000012",
    "title": "여성 스카이블루 벨티드 셔츠 롱 원피스 룩",
    "outfitType": "one_piece",
    "items": [
      {
        "slot": "원피스",
        "name": "스카이블루 카라 벨티드 셔츠 롱 원피스",
        "price": 42000,
        "searchKeyword": "여성 소라 스카이블루 카라 벨트 셔츠 롱 원피스"
      },
      {
        "slot": "신발",
        "name": "화이트 스퀘어토 블록힐 샌들",
        "price": 35000,
        "searchKeyword": "여성 화이트 스퀘어토 미들힐 샌들"
      }
    ]
  },
  {
    "id": "LOOK000013",
    "title": "여성 옐로우 케이블 니트 & 중청 데님 스커트 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "파스텔 옐로우 케이블 꽈배기 니트",
        "price": 27000,
        "searchKeyword": "여성 옐로우 파스텔 꽈배기 라운드넥 니트"
      },
      {
        "slot": "하의",
        "name": "중청 A라인 미디 데님 스커트",
        "price": 31000,
        "searchKeyword": "여성 중청 하이웨스트 A라인 데님 스커트"
      },
      {
        "slot": "신발",
        "name": "브라운 레더 테슬 로퍼",
        "price": 39000,
        "searchKeyword": "여성 브라운 레더 테슬 로퍼"
      }
    ]
  },
  {
    "id": "LOOK000014",
    "title": "여성 차콜 크롭 니트 & 아이보리 와이드 팬츠 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "차콜 그레이 라운드넥 크롭 니트",
        "price": 23000,
        "searchKeyword": "여성 차콜 그레이 라운드넥 크롭 니트"
      },
      {
        "slot": "하의",
        "name": "아이보리 핀턱 와이드 슬랙스",
        "price": 29000,
        "searchKeyword": "여성 아이보리 핀턱 하이웨스트 와이드 슬랙스"
      },
      {
        "slot": "신발",
        "name": "화이트 레더 미니멀 스니커즈",
        "price": 35000,
        "searchKeyword": "여성 화이트 가죽 로우탑 스니커즈"
      }
    ]
  }
];

const MALE_LOOKS = [
  {
    "id": "M2D_LOOK000001",
    "title": "남성 화이트 오버핏 반팔티 & 베이지 와이드 팬츠 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "화이트 코튼 오버핏 반팔 티셔츠",
        "price": 19000,
        "searchKeyword": "남성 화이트 순면 오버핏 무지 반팔티"
      },
      {
        "slot": "하의",
        "name": "베이지 원턱 와이드 치노 팬츠",
        "price": 32000,
        "searchKeyword": "남성 베이지 원턱 와이드 코튼 치노 팬츠"
      },
      {
        "slot": "신발",
        "name": "화이트 클래식 코트화",
        "price": 45000,
        "searchKeyword": "남성 화이트 코트화 레더 스니커즈"
      }
    ]
  },
  {
    "id": "M2D_LOOK000002",
    "title": "남성 네이비 카라 니트 & 연청 와이드 데님 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "다크네이비 오픈카라 반팔 니트",
        "price": 28000,
        "searchKeyword": "남성 네이비 오픈카라 반팔 니트 티셔츠"
      },
      {
        "slot": "하의",
        "name": "연청 세미와이드 테이퍼드 데님 팬츠",
        "price": 34000,
        "searchKeyword": "남성 연청 세미와이드 테이퍼드 청바지"
      },
      {
        "slot": "신발",
        "name": "화이트 독일군 스니커즈",
        "price": 49000,
        "searchKeyword": "남성 독일군 스웨이드 레더 스니커즈"
      }
    ]
  },
  {
    "id": "M2D_LOOK000003",
    "title": "남성 카키 린넨 셔츠 & 베이지 치노 반바지 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "카키 올리브 오버핏 린넨 반팔 셔츠",
        "price": 29000,
        "searchKeyword": "남성 카키 올리브 오버핏 린넨 반팔 셔츠"
      },
      {
        "slot": "하의",
        "name": "베이지 핀턱 코튼 버뮤다 반바지",
        "price": 26000,
        "searchKeyword": "남성 베이지 핀턱 코튼 버뮤다 쇼츠 반바지"
      },
      {
        "slot": "신발",
        "name": "화이트 미니멀 캔버스화",
        "price": 32000,
        "searchKeyword": "남성 화이트 로우탑 캔버스화"
      }
    ]
  },
  {
    "id": "M2D_LOOK000004",
    "title": "남성 올블랙 오버핏 스트릿 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "블랙 헤비웨이트 오버핏 반팔 티셔츠",
        "price": 22000,
        "searchKeyword": "남성 블랙 헤비웨이트 오버핏 반팔티"
      },
      {
        "slot": "하의",
        "name": "블랙 세미와이드 스트레이트 슬랙스",
        "price": 33000,
        "searchKeyword": "남성 블랙 세미와이드 스트레이트 슬랙스"
      },
      {
        "slot": "신발",
        "name": "올블랙 레더 플랫폼 스니커즈",
        "price": 52000,
        "searchKeyword": "남성 올블랙 가죽 레더 스니커즈"
      }
    ]
  },
  {
    "id": "M2D_LOOK000005",
    "title": "남성 스카이블루 셔츠 & 크림 슬랙스 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "스카이블루 스트라이프 옥스포드 셔츠",
        "price": 31000,
        "searchKeyword": "남성 소라 스카이블루 스트라이프 옥스포드 셔츠"
      },
      {
        "slot": "하의",
        "name": "크림 아이보리 테이퍼드 슬랙스",
        "price": 34000,
        "searchKeyword": "남성 크림 아이보리 원턱 테이퍼드 슬랙스"
      },
      {
        "slot": "신발",
        "name": "브라운 스웨이드 페니 로퍼",
        "price": 58000,
        "searchKeyword": "남성 브라운 스웨이드 페니 로퍼"
      }
    ]
  },
  {
    "id": "M2D_LOOK000006",
    "title": "남성 오트밀 니트 & 브라운 와이드 팬츠 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "오트밀 베이지 라운드넥 하프 니트",
        "price": 27000,
        "searchKeyword": "남성 오트밀 베이지 라운드넥 반팔 니트"
      },
      {
        "slot": "하의",
        "name": "모카 브라운 와이드 코튼 팬츠",
        "price": 35000,
        "searchKeyword": "남성 모카 브라운 투턱 와이드 팬츠"
      },
      {
        "slot": "신발",
        "name": "그레이 스웨이드 클래식 러너",
        "price": 53000,
        "searchKeyword": "남성 그레이 스웨이드 레트로 러닝화 스니커즈"
      }
    ]
  },
  {
    "id": "M2D_LOOK000007",
    "title": "남성 화이트 오픈카라 셔츠 & 네이비 슬랙스 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "화이트 린넨 오픈카라 반팔 셔츠",
        "price": 29000,
        "searchKeyword": "남성 화이트 린넨 오픈카라 반팔 셔츠"
      },
      {
        "slot": "하의",
        "name": "다크네이비 세미와이드 슬랙스",
        "price": 36000,
        "searchKeyword": "남성 다크네이비 핀턱 세미와이드 슬랙스"
      },
      {
        "slot": "신발",
        "name": "블랙 플레인토 레더 더비슈즈",
        "price": 62000,
        "searchKeyword": "남성 블랙 플레인토 가죽 더비슈즈"
      }
    ]
  },
  {
    "id": "M2D_LOOK000008",
    "title": "남성 카키 워크자켓 & 베이지 카고 팬츠 룩",
    "outfitType": "outer_set",
    "items": [
      {
        "slot": "아우터",
        "name": "카키 코튼 트러커 워크 자켓",
        "price": 59000,
        "searchKeyword": "남성 카키 올리브 코튼 포켓 워크 자켓"
      },
      {
        "slot": "상의",
        "name": "화이트 라운드넥 기본 반팔티",
        "price": 16000,
        "searchKeyword": "남성 화이트 면 무지 라운드넥 반팔티"
      },
      {
        "slot": "하의",
        "name": "베이지 와이드 멀티포켓 카고 팬츠",
        "price": 38000,
        "searchKeyword": "남성 베이지 와이드 카고 팬츠"
      },
      {
        "slot": "신발",
        "name": "카키 베이지 청키 스니커즈",
        "price": 54000,
        "searchKeyword": "남성 어글리 청키 트레킹화 스니커즈"
      }
    ]
  },
  {
    "id": "M2D_LOOK000009",
    "title": "남성 브릭 오렌지 티셔츠 & 아이보리 팬츠 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "브릭 테라코타 오버핏 반팔 티셔츠",
        "price": 21000,
        "searchKeyword": "남성 테라코타 브릭 오렌지 오버핏 반팔티"
      },
      {
        "slot": "하의",
        "name": "아이보리 코튼 와이드 팬츠",
        "price": 32000,
        "searchKeyword": "남성 아이보리 크림 코튼 와이드 팬츠"
      },
      {
        "slot": "신발",
        "name": "브라운 레더 보트슈즈",
        "price": 48000,
        "searchKeyword": "남성 브라운 가죽 데크 보트슈즈 로퍼"
      }
    ]
  },
  {
    "id": "M2D_LOOK000010",
    "title": "남성 그레이 맨투맨 & 블랙 슬랙스 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "멜란지 그레이 루즈핏 맨투맨 티셔츠",
        "price": 29000,
        "searchKeyword": "남성 멜란지 그레이 오버핏 스웨트셔츠 맨투맨"
      },
      {
        "slot": "하의",
        "name": "블랙 테이퍼드 밴딩 슬랙스",
        "price": 31000,
        "searchKeyword": "남성 블랙 링클프리 테이퍼드 밴딩 슬랙스"
      },
      {
        "slot": "신발",
        "name": "화이트 클래식 캔버스 스니커즈",
        "price": 35000,
        "searchKeyword": "남성 화이트 캔버스 로우탑 스니커즈"
      }
    ]
  },
  {
    "id": "M2D_LOOK000011",
    "title": "남성 아이보리 린넨 셔츠 & 카키 버뮤다 팬츠 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "아이보리 밴드카라 린넨 셔츠",
        "price": 30000,
        "searchKeyword": "남성 아이보리 차이나 밴드카라 린넨 반팔 셔츠"
      },
      {
        "slot": "하의",
        "name": "라이트카키 핀턱 버뮤다 반바지",
        "price": 27000,
        "searchKeyword": "남성 카키 핀턱 버뮤다 쇼츠 치노 반바지"
      },
      {
        "slot": "신발",
        "name": "화이트 가죽 로우탑 스니커즈",
        "price": 45000,
        "searchKeyword": "남성 화이트 레더 심플 로우탑 스니커즈"
      }
    ]
  },
  {
    "id": "M2D_LOOK000012",
    "title": "남성 네이비 블레이저 & 베이지 치노 스마트 캐주얼 룩",
    "outfitType": "outer_set",
    "items": [
      {
        "slot": "아우터",
        "name": "네이비 투버튼 싱글 블레이저 재킷",
        "price": 68000,
        "searchKeyword": "남성 다크네이비 싱글 2버튼 테일러드 블레이저"
      },
      {
        "slot": "상의",
        "name": "화이트 프리미엄 코튼 반팔티",
        "price": 18000,
        "searchKeyword": "남성 화이트 수피마 코튼 이너 반팔티"
      },
      {
        "slot": "하의",
        "name": "베이지 슬림 스트레이트 치노 팬츠",
        "price": 33000,
        "searchKeyword": "남성 베이지 슬림 스트레이트 면바지 치노"
      },
      {
        "slot": "신발",
        "name": "다크브라운 가죽 테슬 로퍼",
        "price": 65000,
        "searchKeyword": "남성 다크브라운 가죽 테슬 로퍼"
      }
    ]
  },
  {
    "id": "M2D_LOOK000013",
    "title": "남성 올리브 린넨 셔츠 & 베이지 이지 팬츠 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "올리브 그린 오픈카라 린넨 셔츠",
        "price": 28000,
        "searchKeyword": "남성 올리브 그린 루즈핏 린넨 반팔 셔츠"
      },
      {
        "slot": "하의",
        "name": "베이지 린넨 밴딩 와이드 팬츠",
        "price": 29000,
        "searchKeyword": "남성 베이지 린넨 혼방 허리밴딩 와이드 팬츠"
      },
      {
        "slot": "신발",
        "name": "브라운 레더 스트랩 슬라이드 샌들",
        "price": 38000,
        "searchKeyword": "남성 브라운 소가죽 스트랩 슬리퍼 샌들"
      }
    ]
  },
  {
    "id": "M2D_LOOK000014",
    "title": "남성 차콜 반팔 니트 & 다크그레이 슬랙스 모노톤 룩",
    "outfitType": "two_piece",
    "items": [
      {
        "slot": "상의",
        "name": "차콜 그레이 모던 라운드넥 반팔 니트",
        "price": 26000,
        "searchKeyword": "남성 차콜 그레이 무지 라운드넥 반팔 니트"
      },
      {
        "slot": "하의",
        "name": "다크그레이 원턱 세미와이드 슬랙스",
        "price": 35000,
        "searchKeyword": "남성 다크그레이 핀턱 세미와이드 슬랙스"
      },
      {
        "slot": "신발",
        "name": "블랙 미니멀 레더 스니커즈",
        "price": 49000,
        "searchKeyword": "남성 블랙 가죽 미니멀 로우탑 스니커즈"
      }
    ]
  }
];

export const DEMOGRAPHIC_GROUPS = [
  {
    "key": "female_10s",
    "gender": "female",
    "age": "10대",
    "label": "여성 10대"
  },
  {
    "key": "female_20s",
    "gender": "female",
    "age": "20대",
    "label": "여성 20대"
  },
  {
    "key": "female_30s",
    "gender": "female",
    "age": "30대",
    "label": "여성 30대"
  },
  {
    "key": "female_40s",
    "gender": "female",
    "age": "40대",
    "label": "여성 40대"
  },
  {
    "key": "female_50s",
    "gender": "female",
    "age": "50대",
    "label": "여성 50대"
  },
  {
    "key": "female_60s",
    "gender": "female",
    "age": "60대",
    "label": "여성 60대"
  },
  {
    "key": "male_10s",
    "gender": "male",
    "age": "10대",
    "label": "남성 10대"
  },
  {
    "key": "male_20s",
    "gender": "male",
    "age": "20대",
    "label": "남성 20대"
  },
  {
    "key": "male_30s",
    "gender": "male",
    "age": "30대",
    "label": "남성 30대"
  },
  {
    "key": "male_40s",
    "gender": "male",
    "age": "40대",
    "label": "남성 40대"
  },
  {
    "key": "male_50s",
    "gender": "male",
    "age": "50대",
    "label": "남성 50대"
  },
  {
    "key": "male_60s",
    "gender": "male",
    "age": "60대",
    "label": "남성 60대"
  }
];

export class OutfitManager {
  constructor() {
    this.categories = {};

    // 1. Female 20s (Existing canonical female looks)
    this.categories.female_20s = FEMALE_LOOKS.map(look => {
      const totalPrice = look.items.reduce((acc, it) => acc + it.price, 0);
      return {
        id: look.id,
        mode: 'female_20s',
        title: `[여성 20대] ${look.title}`,
        image: `/assets/looks/real/${look.id}.jpg`,
        thumbnail: `/assets/looks/real/${look.id}.jpg`,
        totalPrice,
        items: look.items.map(it => ({
          slot: it.slot,
          name: it.name,
          price: it.price,
          coupangUrl: 'https://www.coupang.com',
          searchKeyword: it.searchKeyword
        }))
      };
    });

    // 2. Male 20s (Existing canonical male looks)
    this.categories.male_20s = MALE_LOOKS.map(look => {
      const totalPrice = look.items.reduce((acc, it) => acc + it.price, 0);
      return {
        id: look.id,
        mode: 'male_20s',
        title: `[남성 20대] ${look.title}`,
        image: `/assets/looks/male2d/${look.id}.webp`,
        thumbnail: `/assets/looks/male2d/${look.id}.webp`,
        totalPrice,
        items: look.items.map(it => ({
          slot: it.slot,
          name: it.name,
          price: it.price,
          coupangUrl: 'https://www.coupang.com',
          searchKeyword: it.searchKeyword
        }))
      };
    });

    // 3. New 10 Demographic Groups (10 looks each)
    this.categories.female_10s = [
      {
            "id": "F10_01",
            "mode": "female_10s",
            "title": "[여성 10대] 화이트 카라 반팔티 & 베이지 테니스 스커트 룩",
            "image": "/assets/looks/female_10s/LOOK01.webp",
            "thumbnail": "/assets/looks/female_10s/LOOK01.webp",
            "totalPrice": 67700,
            "items": [
                  {
                        "slot": "상의",
                        "name": "화이트 슬림 카라 반팔 티셔츠",
                        "price": 18900,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 화이트 카라 반팔티"
                  },
                  {
                        "slot": "하의",
                        "name": "베이지 A라인 플리츠 테니스 스커트",
                        "price": 19800,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 베이지 테니스 스커트"
                  },
                  {
                        "slot": "신발",
                        "name": "화이트 캔버스 로우탑 스니커즈",
                        "price": 29000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 화이트 캔버스 스니커즈"
                  }
            ]
      },
      {
            "id": "F10_02",
            "mode": "female_10s",
            "title": "[여성 10대] 스카이블루 스트라이프 린넨 셔츠 & 데님 쇼츠 룩",
            "image": "/assets/looks/female_10s/LOOK02.webp",
            "thumbnail": "/assets/looks/female_10s/LOOK02.webp",
            "totalPrice": 72000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "스카이블루 스트라이프 루즈핏 반팔 셔츠",
                        "price": 24000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 스트라이프 반팔 린넨 셔츠"
                  },
                  {
                        "slot": "하의",
                        "name": "라이트블루 롤업 데님 숏팬츠",
                        "price": 22000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 데님 숏팬츠 반바지"
                  },
                  {
                        "slot": "신발",
                        "name": "더블 스트랩 컴포트 샌들",
                        "price": 26000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 스트랩 컴포트 샌들"
                  }
            ]
      },
      {
            "id": "F10_03",
            "mode": "female_10s",
            "title": "[여성 10대] 소프트 옐로우 퍼프소매 플라워 원피스 룩",
            "image": "/assets/looks/female_10s/LOOK03.webp",
            "thumbnail": "/assets/looks/female_10s/LOOK03.webp",
            "totalPrice": 61000,
            "items": [
                  {
                        "slot": "원피스",
                        "name": "파스텔 옐로우 잔꽃 플라워 퍼프 린넨 원피스",
                        "price": 33000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 옐로우 잔꽃 플라워 린넨 원피스"
                  },
                  {
                        "slot": "신발",
                        "name": "크림 화이트 라운드 슬립온",
                        "price": 28000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 화이트 단화 슬립온"
                  }
            ]
      },
      {
            "id": "F10_04",
            "mode": "female_10s",
            "title": "[여성 10대] 베이비핑크 반팔 그래픽티 & A라인 데님 스커트 룩",
            "image": "/assets/looks/female_10s/LOOK04.webp",
            "thumbnail": "/assets/looks/female_10s/LOOK04.webp",
            "totalPrice": 70800,
            "items": [
                  {
                        "slot": "상의",
                        "name": "베이비핑크 레터링 반팔 티셔츠",
                        "price": 17900,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 핑크 반팔 레터링 티셔츠"
                  },
                  {
                        "slot": "하의",
                        "name": "A라인 중청 데님 미니스커트",
                        "price": 23900,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 A라인 데님 미니스커트"
                  },
                  {
                        "slot": "신발",
                        "name": "화이트 레이스업 하이탑 스니커즈",
                        "price": 29000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "화이트 캔버스 하이탑 스니커즈"
                  }
            ]
      },
      {
            "id": "F10_05",
            "mode": "female_10s",
            "title": "[여성 10대] 파스텔 민트 퍼프 블라우스 & 화이트 플리츠 스커트 룩",
            "image": "/assets/looks/female_10s/LOOK05.webp",
            "thumbnail": "/assets/looks/female_10s/LOOK05.webp",
            "totalPrice": 74500,
            "items": [
                  {
                        "slot": "상의",
                        "name": "파스텔 민트 스퀘어넥 퍼프 반팔 블라우스",
                        "price": 24500,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 민트 퍼프소매 반팔 블라우스"
                  },
                  {
                        "slot": "하의",
                        "name": "화이트 플리츠 셔링 플레어 스커트",
                        "price": 22000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 화이트 플리츠 미니스커트"
                  },
                  {
                        "slot": "신발",
                        "name": "미니멀 플랫 슈즈",
                        "price": 28000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 화이트 플랫 슈즈"
                  }
            ]
      },
      {
            "id": "F10_06",
            "mode": "female_10s",
            "title": "[여성 10대] 그레이 크롭 반팔 후디 & 블랙 쿨링 카고팬츠 룩",
            "image": "/assets/looks/female_10s/LOOK06.webp",
            "thumbnail": "/assets/looks/female_10s/LOOK06.webp",
            "totalPrice": 87000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "멜란지 그레이 크롭 반팔 후드티",
                        "price": 22000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 크롭 반팔 후드티"
                  },
                  {
                        "slot": "하의",
                        "name": "블랙 와이드 쿨링 조거 카고팬츠",
                        "price": 27000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 와이드 쿨링 카고팬츠"
                  },
                  {
                        "slot": "신발",
                        "name": "청키 볼드 레트로 스니커즈",
                        "price": 38000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 어글리 볼드 스니커즈"
                  }
            ]
      },
      {
            "id": "F10_07",
            "mode": "female_10s",
            "title": "[여성 10대] 라벤더 골지 반팔 가디건 & 크림 코튼 쇼츠 룩",
            "image": "/assets/looks/female_10s/LOOK07.webp",
            "thumbnail": "/assets/looks/female_10s/LOOK07.webp",
            "totalPrice": 70900,
            "items": [
                  {
                        "slot": "상의",
                        "name": "라벤더 파스텔 슬림 골지 반팔 가디건",
                        "price": 21900,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 라벤더 반팔 골지 가디건"
                  },
                  {
                        "slot": "하의",
                        "name": "크림 아이보리 코튼 밴딩 반바지",
                        "price": 19000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 코튼 쇼츠 반바지"
                  },
                  {
                        "slot": "신발",
                        "name": "베이지 슬립온 에스파드류",
                        "price": 30000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 에스파드류 슬립온"
                  }
            ]
      },
      {
            "id": "F10_08",
            "mode": "female_10s",
            "title": "[여성 10대] 네이비 세일러 칼라 블라우스 & 그레이 테니스 스커트 룩",
            "image": "/assets/looks/female_10s/LOOK08.webp",
            "thumbnail": "/assets/looks/female_10s/LOOK08.webp",
            "totalPrice": 77000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "네이비 리본 타이 세일러 반팔 블라우스",
                        "price": 25000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 세일러 카라 반팔 블라우스"
                  },
                  {
                        "slot": "하의",
                        "name": "그레이 플리츠 테니스 미니스커트",
                        "price": 20000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 그레이 테니스 스커트"
                  },
                  {
                        "slot": "신발",
                        "name": "클래식 블랙 페니 로퍼",
                        "price": 32000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 블랙 페니 로퍼"
                  }
            ]
      },
      {
            "id": "F10_09",
            "mode": "female_10s",
            "title": "[여성 10대] 버터크림 박시 반팔 셔츠 & 핀턱 버뮤다 쇼츠 룩",
            "image": "/assets/looks/female_10s/LOOK09.webp",
            "thumbnail": "/assets/looks/female_10s/LOOK09.webp",
            "totalPrice": 73800,
            "items": [
                  {
                        "slot": "상의",
                        "name": "버터크림 오픈카라 박시 반팔 셔츠",
                        "price": 23900,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 반팔 오픈카라 린넨 셔츠"
                  },
                  {
                        "slot": "하의",
                        "name": "베이지 카키 투핀턱 버뮤다 숏팬츠",
                        "price": 21900,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 핀턱 버뮤다 쇼츠"
                  },
                  {
                        "slot": "신발",
                        "name": "브라운 크로스 스트랩 슬리퍼 샌들",
                        "price": 28000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 크로스 스트랩 샌들"
                  }
            ]
      },
      {
            "id": "F10_10",
            "mode": "female_10s",
            "title": "[여성 10대] 스카이블루 스퀘어넥 반팔 니트 & 아이보리 와이드 슬랙스 룩",
            "image": "/assets/looks/female_10s/LOOK10.webp",
            "thumbnail": "/assets/looks/female_10s/LOOK10.webp",
            "totalPrice": 78900,
            "items": [
                  {
                        "slot": "상의",
                        "name": "소프트 스카이블루 스퀘어넥 슬림 반팔 니트",
                        "price": 21900,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 스퀘어넥 반팔 여름 니트"
                  },
                  {
                        "slot": "하의",
                        "name": "아이보리 린넨 와이드 롱 슬랙스",
                        "price": 28000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 린넨 와이드 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "화이트 심플 로우 스니커즈",
                        "price": 29000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 화이트 심플 스니커즈"
                  }
            ]
      }
];

    this.categories.female_30s = [
      {
            "id": "F30_01",
            "mode": "female_30s",
            "title": "[여성 30대] 네이비 테일러드 자켓 & 베이지 슬랙스 룩",
            "image": "/assets/looks/female_30s/LOOK01.webp",
            "thumbnail": "/assets/looks/female_30s/LOOK01.webp",
            "totalPrice": 142000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "테일러드 싱글 린넨 자켓",
                        "price": 58000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 네이비 싱글 테일러드 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "하이웨스트 핀턱 와이드 슬랙스",
                        "price": 39000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 핀턱 와이드 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "클래식 레더 페니 로퍼",
                        "price": 45000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 소가죽 페니 로퍼"
                  }
            ]
      },
      {
            "id": "F30_02",
            "mode": "female_30s",
            "title": "[여성 30대] 클래식 더블 트렌치코트 & 스트레이트 데님 룩",
            "image": "/assets/looks/female_30s/LOOK02.webp",
            "thumbnail": "/assets/looks/female_30s/LOOK02.webp",
            "totalPrice": 176000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "더블버튼 벨티드 롱 트렌치코트",
                        "price": 89000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 더블 롱 트렌치코트"
                  },
                  {
                        "slot": "하의",
                        "name": "슬림 스트레이트 중청 데님",
                        "price": 38000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 슬림 일자 데님 팬츠"
                  },
                  {
                        "slot": "신발",
                        "name": "블랙 가죽 삭스 앵클부츠",
                        "price": 49000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 가죽 삭스 앵클부츠"
                  }
            ]
      },
      {
            "id": "F30_03",
            "mode": "female_30s",
            "title": "[여성 30대] 차콜 슬림 셋업 수트 & 스트라이프 셔츠 룩",
            "image": "/assets/looks/female_30s/LOOK03.webp",
            "thumbnail": "/assets/looks/female_30s/LOOK03.webp",
            "totalPrice": 169000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "차콜 슬림핏 테일러드 셋업 수트",
                        "price": 95000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 셋업 정장 수트"
                  },
                  {
                        "slot": "하의",
                        "name": "스트라이프 코튼 드레스 셔츠",
                        "price": 32000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 슬림 스트라이프 셔츠"
                  },
                  {
                        "slot": "신발",
                        "name": "포인티드 스틸레토 펌프스",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 포인티드 토 펌프스"
                  }
            ]
      },
      {
            "id": "F30_04",
            "mode": "female_30s",
            "title": "[여성 30대] 루즈핏 캐시미어 니트 & 딥그린 플리츠 스커트 룩",
            "image": "/assets/looks/female_30s/LOOK04.webp",
            "thumbnail": "/assets/looks/female_30s/LOOK04.webp",
            "totalPrice": 128000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "오트밀 소프트 캐시미어 블렌드 니트",
                        "price": 48000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 캐시미어 라운드 니트"
                  },
                  {
                        "slot": "하의",
                        "name": "딥그린 롱 아코디언 플리츠 스커트",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 롱 플리츠 스커트"
                  },
                  {
                        "slot": "신발",
                        "name": "그린 메리제인 플랫슈즈",
                        "price": 38000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 플랫 메리제인"
                  }
            ]
      },
      {
            "id": "F30_05",
            "mode": "female_30s",
            "title": "[여성 30대] 블랙 노카라 자켓 & 핀턱 슬랙스 모던 룩",
            "image": "/assets/looks/female_30s/LOOK05.webp",
            "thumbnail": "/assets/looks/female_30s/LOOK05.webp",
            "totalPrice": 145000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "블랙 슬림 노카라 자켓",
                        "price": 62000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 블랙 노카라 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "블랙 스트레이트 핀턱 슬랙스",
                        "price": 39000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 스트레이트 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "블랙 슬링백 플랫슈즈",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 블랙 슬링백 펌프스"
                  }
            ]
      },
      {
            "id": "F30_06",
            "mode": "female_30s",
            "title": "[여성 30대] 루즈핏 화이트 셔츠 & 네이비 H라인 스커트 룩",
            "image": "/assets/looks/female_30s/LOOK06.webp",
            "thumbnail": "/assets/looks/female_30s/LOOK06.webp",
            "totalPrice": 117000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "프리미엄 옥스퍼드 오버핏 셔츠",
                        "price": 36000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 루즈핏 화이트 셔츠"
                  },
                  {
                        "slot": "하의",
                        "name": "하이웨스트 H라인 미디스커트",
                        "price": 35000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 H라인 미디스커트"
                  },
                  {
                        "slot": "신발",
                        "name": "블랙 가죽 로퍼",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 클래식 가죽 로퍼"
                  }
            ]
      },
      {
            "id": "F30_07",
            "mode": "female_30s",
            "title": "[여성 30대] 소프트 브라운 니트 가디건 & 그레이 테이퍼드 슬랙스 룩",
            "image": "/assets/looks/female_30s/LOOK07.webp",
            "thumbnail": "/assets/looks/female_30s/LOOK07.webp",
            "totalPrice": 125000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "V넥 립조직 울 니트 가디건",
                        "price": 45000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 V넥 울 니트 가디건"
                  },
                  {
                        "slot": "하의",
                        "name": "테이퍼드 크롭 핀턱 슬랙스",
                        "price": 38000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 핀턱 테이퍼드 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "미니멀 레더 코트화",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 가죽 미니멀 스니커즈"
                  }
            ]
      },
      {
            "id": "F30_08",
            "mode": "female_30s",
            "title": "[여성 30대] 브릭 브라운 벨티드 랩 롱원피스 룩",
            "image": "/assets/looks/female_30s/LOOK08.webp",
            "thumbnail": "/assets/looks/female_30s/LOOK08.webp",
            "totalPrice": 136000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "벨티드 V넥 랩 플레어 롱원피스",
                        "price": 56000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 V넥 벨티드 롱원피스"
                  },
                  {
                        "slot": "하의",
                        "name": "소가죽 스퀘어토 미들 앵클부츠",
                        "price": 58000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 스퀘어토 앵클부츠"
                  },
                  {
                        "slot": "신발",
                        "name": "골드 펜던트 넥클리스",
                        "price": 22000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 심플 골드 목걸이"
                  }
            ]
      },
      {
            "id": "F30_09",
            "mode": "female_30s",
            "title": "[여성 30대] 보트넥 스트라이프 니트 & 화이트 와이드 슬랙스 룩",
            "image": "/assets/looks/female_30s/LOOK09.webp",
            "thumbnail": "/assets/looks/female_30s/LOOK09.webp",
            "totalPrice": 112000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "보트넥 파리지앵 스트라이프 니트",
                        "price": 34000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 보트넥 스트라이프 니트"
                  },
                  {
                        "slot": "하의",
                        "name": "화이트 하이웨스트 와이드 팬츠",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 화이트 와이드 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "스트랩 레더 샌들 슬리퍼",
                        "price": 36000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 가죽 스트랩 샌들"
                  }
            ]
      },
      {
            "id": "F30_10",
            "mode": "female_30s",
            "title": "[여성 30대] 파스텔 핑크 자켓 & 크롭 일자 데님 룩",
            "image": "/assets/looks/female_30s/LOOK10.webp",
            "thumbnail": "/assets/looks/female_30s/LOOK10.webp",
            "totalPrice": 148000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "싱글 투버튼 파스텔 테일러드 자켓",
                        "price": 64000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 파스텔 테일러드 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "크롭 스트레이트 연청 데님",
                        "price": 39000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 크롭 일자 청바지"
                  },
                  {
                        "slot": "신발",
                        "name": "누드톤 포인티드 펌프스",
                        "price": 45000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 스킨톤 슬링백 힐"
                  }
            ]
      }
];

    this.categories.female_40s = [
      {
            "id": "F40_01",
            "mode": "female_40s",
            "title": "[여성 40대] 카멜 소프트 터틀 니트 & 실크 스카프 슬랙스 룩",
            "image": "/assets/looks/female_40s/LOOK01.webp",
            "thumbnail": "/assets/looks/female_40s/LOOK01.webp",
            "totalPrice": 151000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "카멜 파인 울 크루넥 니트",
                        "price": 54000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 울 캐시미어 니트"
                  },
                  {
                        "slot": "하의",
                        "name": "차콜 핀턱 와이드 슬랙스",
                        "price": 45000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 핀턱 와이드 팬츠"
                  },
                  {
                        "slot": "신발",
                        "name": "클래식 비트 로퍼",
                        "price": 52000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 가죽 홀스빗 로퍼"
                  }
            ]
      },
      {
            "id": "F40_02",
            "mode": "female_40s",
            "title": "[여성 40대] 에메랄드 그린 벨티드 랩 드레스 룩",
            "image": "/assets/looks/female_40s/LOOK02.webp",
            "thumbnail": "/assets/looks/female_40s/LOOK02.webp",
            "totalPrice": 154000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "벨티드 V넥 실루엣 랩 원피스",
                        "price": 68000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 랩 플레어 롱원피스"
                  },
                  {
                        "slot": "하의",
                        "name": "소가죽 스퀘어토 앵클부츠",
                        "price": 62000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 스퀘어토 앵클부츠"
                  },
                  {
                        "slot": "신발",
                        "name": "골드 체인 네크리스",
                        "price": 24000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 14k 도금 골드 목걸이"
                  }
            ]
      },
      {
            "id": "F40_03",
            "mode": "female_40s",
            "title": "[여성 40대] 아이보리 롱 가디건 & 네이비 크롭 슬랙스 룩",
            "image": "/assets/looks/female_40s/LOOK03.webp",
            "thumbnail": "/assets/looks/female_40s/LOOK03.webp",
            "totalPrice": 164000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "오픈형 울 블렌드 롱 가디건",
                        "price": 62000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 루즈핏 롱 가디건"
                  },
                  {
                        "slot": "하의",
                        "name": "스트라이프 셔츠 & 슬랙스 세트",
                        "price": 58000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 핀턱 크롭 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "포인티드 레더 블로퍼",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 가죽 블로퍼"
                  }
            ]
      },
      {
            "id": "F40_04",
            "mode": "female_40s",
            "title": "[여성 40대] 네이비 클래식 자켓 & 그레이 핀턱 슬랙스 룩",
            "image": "/assets/looks/female_40s/LOOK04.webp",
            "thumbnail": "/assets/looks/female_40s/LOOK04.webp",
            "totalPrice": 170000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "테일러드 원버튼 포멀 자켓",
                        "price": 76000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 원버튼 테일러드 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "소프트 그레이 스트레이트 슬랙스",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 일자 정장 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "클래식 페니 로퍼",
                        "price": 48000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 클래식 가죽 로퍼"
                  }
            ]
      },
      {
            "id": "F40_05",
            "mode": "female_40s",
            "title": "[여성 40대] 베이지 벨티드 트렌치코트 & 플로럴 롱원피스 룩",
            "image": "/assets/looks/female_40s/LOOK05.webp",
            "thumbnail": "/assets/looks/female_40s/LOOK05.webp",
            "totalPrice": 198000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "더블 버튼 벨티드 롱 트렌치코트",
                        "price": 98000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 더블 롱 트렌치코트"
                  },
                  {
                        "slot": "하의",
                        "name": "차분한 톤 플로럴 쉬폰 롱원피스",
                        "price": 54000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 플로럴 쉬폰 롱원피스"
                  },
                  {
                        "slot": "신발",
                        "name": "누드베이지 포인티드 펌프스",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 포인티드 펌프스"
                  }
            ]
      },
      {
            "id": "F40_06",
            "mode": "female_40s",
            "title": "[여성 40대] 그레이 롱 니트 가디건 & 아이보리 와이드 팬츠 룩",
            "image": "/assets/looks/female_40s/LOOK06.webp",
            "thumbnail": "/assets/looks/female_40s/LOOK06.webp",
            "totalPrice": 153000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "소프트 포켓 롱 니트 가디건",
                        "price": 58000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 포켓 롱 가디건"
                  },
                  {
                        "slot": "하의",
                        "name": "아이보리 핀턱 와이드 슬랙스",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 아이보리 와이드 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "스퀘어토 가죽 펌프스",
                        "price": 49000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 스퀘어토 미들힐"
                  }
            ]
      },
      {
            "id": "F40_07",
            "mode": "female_40s",
            "title": "[여성 40대] 베이지 슬림 니트 & 테라코타 플리츠 롱스커트 룩",
            "image": "/assets/looks/female_40s/LOOK07.webp",
            "thumbnail": "/assets/looks/female_40s/LOOK07.webp",
            "totalPrice": 133000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "소프트 파인 골지 슬림 니트",
                        "price": 39000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 슬림 골지 니트"
                  },
                  {
                        "slot": "하의",
                        "name": "테라코타 롱 플리츠 스커트",
                        "price": 48000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 아코디언 롱 플리츠 스커트"
                  },
                  {
                        "slot": "신발",
                        "name": "스웨이드 슬링백 펌프스",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 스웨이드 슬링백 힐"
                  }
            ]
      },
      {
            "id": "F40_08",
            "mode": "female_40s",
            "title": "[여성 40대] 카멜 더블 오버코트 & 니트 원피스 룩",
            "image": "/assets/looks/female_40s/LOOK08.webp",
            "thumbnail": "/assets/looks/female_40s/LOOK08.webp",
            "totalPrice": 265000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "울 블렌드 더블 체스터 코트",
                        "price": 128000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 핸드메이드 울 롱코트"
                  },
                  {
                        "slot": "하의",
                        "name": "터틀넥 니트 롱 원피스",
                        "price": 58000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 터틀넥 니트 롱원피스"
                  },
                  {
                        "slot": "신발",
                        "name": "레더 롱 라이딩 부츠",
                        "price": 79000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 가죽 롱부츠"
                  }
            ]
      },
      {
            "id": "F40_09",
            "mode": "female_40s",
            "title": "[여성 40대] 블랙 루즈핏 니트 & 차콜 스트레이트 팬츠 룩",
            "image": "/assets/looks/female_40s/LOOK09.webp",
            "thumbnail": "/assets/looks/female_40s/LOOK09.webp",
            "totalPrice": 155000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "프리미엄 캐시미어 보트넥 니트",
                        "price": 65000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 캐시미어 보트넥 니트"
                  },
                  {
                        "slot": "하의",
                        "name": "차콜 슬림 스트레이트 슬랙스",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 스트레이트 정장 바지"
                  },
                  {
                        "slot": "신발",
                        "name": "스퀘어토 가죽 플랫 슈즈",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 스퀘어토 가죽 플랫"
                  }
            ]
      },
      {
            "id": "F40_10",
            "mode": "female_40s",
            "title": "[여성 40대] 트위드 숏 자켓 & 슬림 스트레이트 데님 룩",
            "image": "/assets/looks/female_40s/LOOK10.webp",
            "thumbnail": "/assets/looks/female_40s/LOOK10.webp",
            "totalPrice": 175000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "프렌치 무드 배색 트위드 자켓",
                        "price": 84000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 배색 트위드 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "슬림핏 다크 워싱 데님 팬츠",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 슬림 스트레이트 데님"
                  },
                  {
                        "slot": "신발",
                        "name": "클래식 홀스빗 로퍼",
                        "price": 49000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 홀스빗 가죽 로퍼"
                  }
            ]
      }
];

    this.categories.female_50s = [
      {
            "id": "F50_01",
            "mode": "female_50s",
            "title": "[여성 50대] 네이비 비대칭 드레이프 튜닉 & 화이트 코튼 팬츠 룩",
            "image": "/assets/looks/female_50s/LOOK01.webp",
            "thumbnail": "/assets/looks/female_50s/LOOK01.webp",
            "totalPrice": 133000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "네이비 실크 혼방 롱 튜닉 블라우스",
                        "price": 48000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 실크 롱 튜닉 블라우스"
                  },
                  {
                        "slot": "하의",
                        "name": "화이트 스트레이트 밴딩 팬츠",
                        "price": 39000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 편한 밴딩 면바지"
                  },
                  {
                        "slot": "신발",
                        "name": "브라운 컴포트 가죽 로퍼",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 발편한 가죽 로퍼"
                  }
            ]
      },
      {
            "id": "F50_02",
            "mode": "female_50s",
            "title": "[여성 50대] 베이지 니트 가디건 & 차콜 밴딩 슬랙스 룩",
            "image": "/assets/looks/female_50s/LOOK02.webp",
            "thumbnail": "/assets/looks/female_50s/LOOK02.webp",
            "totalPrice": 138000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "부클레 텍스처 배색 가디건",
                        "price": 52000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 부클레 니트 가디건"
                  },
                  {
                        "slot": "하의",
                        "name": "차콜 신축성 테이퍼드 슬랙스",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 테이퍼드 슬랙스 밴딩"
                  },
                  {
                        "slot": "신발",
                        "name": "소프트 가죽 컴포트 플랫",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 쿠션 컴포트 슈즈"
                  }
            ]
      },
      {
            "id": "F50_03",
            "mode": "female_50s",
            "title": "[여성 50대] 인디고 린넨 셔츠 롱원피스 룩",
            "image": "/assets/looks/female_50s/LOOK03.webp",
            "thumbnail": "/assets/looks/female_50s/LOOK03.webp",
            "totalPrice": 135000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "워싱 린넨 벨티드 셔츠 롱원피스",
                        "price": 65000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 린넨 셔츠 롱원피스"
                  },
                  {
                        "slot": "하의",
                        "name": "소가죽 스퀘어 슬립온",
                        "price": 48000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 소가죽 슬립온"
                  },
                  {
                        "slot": "신발",
                        "name": "심플 실버 롱 목걸이",
                        "price": 22000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 실버 롱 펜던트 목걸이"
                  }
            ]
      },
      {
            "id": "F50_04",
            "mode": "female_50s",
            "title": "[여성 50대] 청록 싱글 자켓 & 블랙 핀턱 팬츠 룩",
            "image": "/assets/looks/female_50s/LOOK04.webp",
            "thumbnail": "/assets/looks/female_50s/LOOK04.webp",
            "totalPrice": 169000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "라이트 패딩 안감 싱글 블레이저",
                        "price": 78000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 클래식 싱글 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "블랙 일자 핀턱 슬랙스",
                        "price": 45000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 일자 핀턱 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "클래식 로우힐 로퍼",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 로우힐 페니 로퍼"
                  }
            ]
      },
      {
            "id": "F50_05",
            "mode": "female_50s",
            "title": "[여성 50대] 아이보리 니트 & 인디핑크 아코디언 플리츠 스커트 룩",
            "image": "/assets/looks/female_50s/LOOK05.webp",
            "thumbnail": "/assets/looks/female_50s/LOOK05.webp",
            "totalPrice": 135000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "보트넥 소프트 파인 니트",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 보트넥 파인 니트"
                  },
                  {
                        "slot": "하의",
                        "name": "인디핑크 롱 아코디언 스커트",
                        "price": 48000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 롱 플리츠 스커트"
                  },
                  {
                        "slot": "신발",
                        "name": "베이지 스킨톤 키튼힐",
                        "price": 45000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 키튼힐 펌프스"
                  }
            ]
      },
      {
            "id": "F50_06",
            "mode": "female_50s",
            "title": "[여성 50대] 베이지 싱글 코트 & 스트라이프 티 룩",
            "image": "/assets/looks/female_50s/LOOK06.webp",
            "thumbnail": "/assets/looks/female_50s/LOOK06.webp",
            "totalPrice": 164000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "경량 메모리 패브릭 싱글 롱코트",
                        "price": 89000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 경량 봄가을 롱코트"
                  },
                  {
                        "slot": "하의",
                        "name": "코튼 스트라이프 티셔츠",
                        "price": 26000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 코튼 스트라이프 티셔츠"
                  },
                  {
                        "slot": "신발",
                        "name": "가죽 워킹 스니커즈",
                        "price": 49000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 천연가죽 워킹화"
                  }
            ]
      },
      {
            "id": "F50_07",
            "mode": "female_50s",
            "title": "[여성 50대] 옐로우 플로럴 블라우스 & 베이지 슬랙스 룩",
            "image": "/assets/looks/female_50s/LOOK07.webp",
            "thumbnail": "/assets/looks/female_50s/LOOK07.webp",
            "totalPrice": 125000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "소프트 플로럴 프린트 셔링 블라우스",
                        "price": 45000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 플로럴 셔링 블라우스"
                  },
                  {
                        "slot": "하의",
                        "name": "베이지 밴딩 핀턱 슬랙스",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 베이지 슬랙스 밴딩"
                  },
                  {
                        "slot": "신발",
                        "name": "스트랩 가죽 플랫 샌들",
                        "price": 38000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 가죽 플랫 샌들"
                  }
            ]
      },
      {
            "id": "F50_08",
            "mode": "female_50s",
            "title": "[여성 50대] 올리브 롱 스웨터 & 레이어드 셔츠 슬랙스 룩",
            "image": "/assets/looks/female_50s/LOOK08.webp",
            "thumbnail": "/assets/looks/female_50s/LOOK08.webp",
            "totalPrice": 141000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "터틀 레이어드 울 니트 스웨터",
                        "price": 56000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 레이어드 니트 스웨터"
                  },
                  {
                        "slot": "하의",
                        "name": "블랙 슬림핏 컴포트 팬츠",
                        "price": 39000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 슬림핏 컴포트 팬츠"
                  },
                  {
                        "slot": "신발",
                        "name": "버건디 클래식 로퍼",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 클래식 로퍼"
                  }
            ]
      },
      {
            "id": "F50_09",
            "mode": "female_50s",
            "title": "[여성 50대] 버건디 드레이프 가디건 & 아이보리 팬츠 룩",
            "image": "/assets/looks/female_50s/LOOK09.webp",
            "thumbnail": "/assets/looks/female_50s/LOOK09.webp",
            "totalPrice": 148000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "숄칼라 드레이프 니트 가디건",
                        "price": 58000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 숄카라 니트 가디건"
                  },
                  {
                        "slot": "하의",
                        "name": "아이보리 릴렉스 핏 팬츠",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 와이드 릴렉스 팬츠"
                  },
                  {
                        "slot": "신발",
                        "name": "그레이 스웨이드 로우힐",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 스웨이드 로우힐"
                  }
            ]
      },
      {
            "id": "F50_10",
            "mode": "female_50s",
            "title": "[여성 50대] 차콜 노카라 롱자켓 & 그레이 슬랙스 룩",
            "image": "/assets/looks/female_50s/LOOK10.webp",
            "thumbnail": "/assets/looks/female_50s/LOOK10.webp",
            "totalPrice": 176000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "미니멀 노카라 울 블렌드 롱자켓",
                        "price": 82000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 노카라 롱자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "그레이 스트레이트 핏 슬랙스",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 그레이 일자 바지"
                  },
                  {
                        "slot": "신발",
                        "name": "소가죽 컴포트 슬립온 로퍼",
                        "price": 48000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 가죽 컴포트 로퍼"
                  }
            ]
      }
];

    this.categories.female_60s = [
      {
            "id": "F60_01",
            "mode": "female_60s",
            "title": "[여성 60대] 세이지 그린 니트 가디건 & 차콜 슬랙스 룩",
            "image": "/assets/looks/female_60s/LOOK01.webp",
            "thumbnail": "/assets/looks/female_60s/LOOK01.webp",
            "totalPrice": 132000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "소프트 울 버튼 가디건",
                        "price": 49000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "시니어 여성 울 가디건"
                  },
                  {
                        "slot": "하의",
                        "name": "차콜 허리밴딩 컴포트 슬랙스",
                        "price": 38000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "시니어 여성 밴딩 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "쿠션 컴포트 가죽 로퍼",
                        "price": 45000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 기능성 컴포트 로퍼"
                  }
            ]
      },
      {
            "id": "F60_02",
            "mode": "female_60s",
            "title": "[여성 60대] 라이트블루 경량 다운 베스트 & 네이비 팬츠 룩",
            "image": "/assets/looks/female_60s/LOOK02.webp",
            "thumbnail": "/assets/looks/female_60s/LOOK02.webp",
            "totalPrice": 129000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "초경량 패딩 퀼팅 조끼",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 경량 패딩 조끼"
                  },
                  {
                        "slot": "하의",
                        "name": "네이비 신축성 코튼 슬랙스",
                        "price": 36000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 스판 밴딩 바지"
                  },
                  {
                        "slot": "신발",
                        "name": "발편한 다이얼 워킹화",
                        "price": 49000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 다이얼 워킹화"
                  }
            ]
      },
      {
            "id": "F60_03",
            "mode": "female_60s",
            "title": "[여성 60대] 베이지 트렌치 코트 & 카키 팬츠 룩",
            "image": "/assets/looks/female_60s/LOOK03.webp",
            "thumbnail": "/assets/looks/female_60s/LOOK03.webp",
            "totalPrice": 159000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "생활방수 싱글 하프 트렌치코트",
                        "price": 79000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 하프 트렌치코트"
                  },
                  {
                        "slot": "하의",
                        "name": "올리브 카키 스트레이트 슬랙스",
                        "price": 38000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 카키 스트레이트 바지"
                  },
                  {
                        "slot": "신발",
                        "name": "가죽 슬립온 로퍼",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 가죽 슬립온 슈즈"
                  }
            ]
      },
      {
            "id": "F60_04",
            "mode": "female_60s",
            "title": "[여성 60대] 더스티 핑크 롱 가디건 & 베이지 팬츠 룩",
            "image": "/assets/looks/female_60s/LOOK04.webp",
            "thumbnail": "/assets/looks/female_60s/LOOK04.webp",
            "totalPrice": 134000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "소프트 롱 니트 가디건",
                        "price": 52000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 소프트 롱 가디건"
                  },
                  {
                        "slot": "하의",
                        "name": "베이지 코튼 스트레이트 슬랙스",
                        "price": 38000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 베이지 면바지 밴딩"
                  },
                  {
                        "slot": "신발",
                        "name": "스웨이드 플랫 로퍼",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 스웨이드 플랫"
                  }
            ]
      },
      {
            "id": "F60_05",
            "mode": "female_60s",
            "title": "[여성 60대] 청록 니트 가디건 & 울 머플러 슬랙스 룩",
            "image": "/assets/looks/female_60s/LOOK05.webp",
            "thumbnail": "/assets/looks/female_60s/LOOK05.webp",
            "totalPrice": 124000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "루즈핏 브이넥 니트 가디건",
                        "price": 54000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 루즈핏 니트 가디건"
                  },
                  {
                        "slot": "하의",
                        "name": "체크 울 머플러 스카프",
                        "price": 24000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "울 캐시미어 머플러"
                  },
                  {
                        "slot": "신발",
                        "name": "그레이 워킹 슈즈",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 쿠션 워킹화"
                  }
            ]
      },
      {
            "id": "F60_06",
            "mode": "female_60s",
            "title": "[여성 60대] 네이비 후드 바람막이 사파리 자켓 룩",
            "image": "/assets/looks/female_60s/LOOK06.webp",
            "thumbnail": "/assets/looks/female_60s/LOOK06.webp",
            "totalPrice": 158000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "경량 스트링 후드 사파리 점퍼",
                        "price": 68000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 사파리 바람막이 점퍼"
                  },
                  {
                        "slot": "하의",
                        "name": "베이지 스트레이트 팬츠",
                        "price": 38000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 스트레이트 팬츠 밴딩"
                  },
                  {
                        "slot": "신발",
                        "name": "경량 트레킹화",
                        "price": 52000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 경량 트레킹화"
                  }
            ]
      },
      {
            "id": "F60_07",
            "mode": "female_60s",
            "title": "[여성 60대] 오트밀 브이넥 니트 베스트 & 플리츠 스커트 룩",
            "image": "/assets/looks/female_60s/LOOK07.webp",
            "thumbnail": "/assets/looks/female_60s/LOOK07.webp",
            "totalPrice": 125000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "클래식 케이블 니트 조끼",
                        "price": 38000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 케이블 니트 베스트"
                  },
                  {
                        "slot": "하의",
                        "name": "차콜 H라인 플리츠 롱스커트",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 밴딩 롱스커트"
                  },
                  {
                        "slot": "신발",
                        "name": "단정한 가죽 로퍼",
                        "price": 45000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 소가죽 로퍼"
                  }
            ]
      },
      {
            "id": "F60_08",
            "mode": "female_60s",
            "title": "[여성 60대] 라벤더 싱글 자켓 셋업 룩",
            "image": "/assets/looks/female_60s/LOOK08.webp",
            "thumbnail": "/assets/looks/female_60s/LOOK08.webp",
            "totalPrice": 158000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "파스텔 라벤더 린넨 혼방 자켓",
                        "price": 74000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 파스텔 린넨 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "화이트 스트레이트 팬츠",
                        "price": 40000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 화이트 일자 바지"
                  },
                  {
                        "slot": "신발",
                        "name": "가죽 슬링백 플랫",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 가죽 플랫 슈즈"
                  }
            ]
      },
      {
            "id": "F60_09",
            "mode": "female_60s",
            "title": "[여성 60대] 브라운 노르딕 니트 가디건 & 베이지 팬츠 룩",
            "image": "/assets/looks/female_60s/LOOK09.webp",
            "thumbnail": "/assets/looks/female_60s/LOOK09.webp",
            "totalPrice": 142000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "노르딕 자카드 울 니트 가디건",
                        "price": 58000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 자카드 니트 가디건"
                  },
                  {
                        "slot": "하의",
                        "name": "베이지 코튼 슬랙스",
                        "price": 38000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 코튼 일자 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "가죽 모카신 로퍼",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 모카신 가죽 로퍼"
                  }
            ]
      },
      {
            "id": "F60_10",
            "mode": "female_60s",
            "title": "[여성 60대] 머스터드 패딩 점퍼 & 네이비 팬츠 룩",
            "image": "/assets/looks/female_60s/LOOK10.webp",
            "thumbnail": "/assets/looks/female_60s/LOOK10.webp",
            "totalPrice": 148000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "초경량 퀼팅 버튼 숏점퍼",
                        "price": 64000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 경량 퀼팅 숏점퍼"
                  },
                  {
                        "slot": "하의",
                        "name": "네이비 스트레이트 밴딩 바지",
                        "price": 38000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 밴딩 일자 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "스웨이드 컴포트 슈즈",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "여성 스웨이드 편한 신발"
                  }
            ]
      }
];

    this.categories.male_10s = [
      {
            "id": "M10_01",
            "mode": "male_10s",
            "title": "[남성 10대] 네이비 바시티 자켓 & 와이드 카고 팬츠 룩",
            "image": "/assets/looks/male_10s/LOOK01.webp",
            "thumbnail": "/assets/looks/male_10s/LOOK01.webp",
            "totalPrice": 135000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "클래식 울 바시티 스타디움 자켓",
                        "price": 59000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 바시티 야구 점퍼"
                  },
                  {
                        "slot": "하의",
                        "name": "다크그레이 와이드 포켓 카고팬츠",
                        "price": 34000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 와이드 카고팬츠"
                  },
                  {
                        "slot": "신발",
                        "name": "클래식 청키 화이트 스니커즈",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 청키 스니커즈"
                  }
            ]
      },
      {
            "id": "M10_02",
            "mode": "male_10s",
            "title": "[남성 10대] 오버핏 레터링 후드티 & 와이드 데님 팬츠 룩",
            "image": "/assets/looks/male_10s/LOOK02.webp",
            "thumbnail": "/assets/looks/male_10s/LOOK02.webp",
            "totalPrice": 119000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "빈티지 레터링 오버핏 기모 후드티",
                        "price": 36000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 오버핏 레터링 후드티"
                  },
                  {
                        "slot": "하의",
                        "name": "와이드 핏 워싱 데님 팬츠",
                        "price": 35000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 와이드 데님 팬츠"
                  },
                  {
                        "slot": "신발",
                        "name": "하이탑 농구화 스니커즈",
                        "price": 48000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 하이탑 스니커즈"
                  }
            ]
      },
      {
            "id": "M10_03",
            "mode": "male_10s",
            "title": "[남성 10대] 윈드브레이커 바람막이 & 조거 카고팬츠 룩",
            "image": "/assets/looks/male_10s/LOOK03.webp",
            "thumbnail": "/assets/looks/male_10s/LOOK03.webp",
            "totalPrice": 121000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "미니멀 하이넥 윈드브레이커 자켓",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 바람막이 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "블랙 나일론 조거 카고팬츠",
                        "price": 32000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 조거 카고팬츠"
                  },
                  {
                        "slot": "신발",
                        "name": "러닝 메쉬 스니커즈",
                        "price": 45000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 메쉬 러닝화"
                  }
            ]
      },
      {
            "id": "M10_04",
            "mode": "male_10s",
            "title": "[남성 10대] 중청 데님 트러커 자켓 & 와이드 슬랙스 룩",
            "image": "/assets/looks/male_10s/LOOK04.webp",
            "thumbnail": "/assets/looks/male_10s/LOOK04.webp",
            "totalPrice": 110000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "오버사이즈 빈티지 데님 자켓",
                        "price": 48000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 오버핏 청자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "블랙 원턱 와이드 슬랙스",
                        "price": 33000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 와이드 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "캔버스 클래식 스니커즈",
                        "price": 29000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 캔버스 스니커즈"
                  }
            ]
      },
      {
            "id": "M10_05",
            "mode": "male_10s",
            "title": "[남성 10대] 그린 니트 베스트 & 오버핏 셔츠 와이드 팬츠 룩",
            "image": "/assets/looks/male_10s/LOOK05.webp",
            "thumbnail": "/assets/looks/male_10s/LOOK05.webp",
            "totalPrice": 100000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "V넥 루즈핏 케이블 니트 베스트",
                        "price": 28000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 V넥 니트 조끼"
                  },
                  {
                        "slot": "하의",
                        "name": "차콜 와이드 벌룬 팬츠",
                        "price": 34000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 와이드 벌룬 팬츠"
                  },
                  {
                        "slot": "신발",
                        "name": "스웨이드 로우 스니커즈",
                        "price": 38000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 스웨이드 스니커즈"
                  }
            ]
      },
      {
            "id": "M10_06",
            "mode": "male_10s",
            "title": "[남성 10대] 패딩 조끼 & 그레이 후드티 카고팬츠 룩",
            "image": "/assets/looks/male_10s/LOOK06.webp",
            "thumbnail": "/assets/looks/male_10s/LOOK06.webp",
            "totalPrice": 125000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "스탠드넥 볼륨 패딩 베스트",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 패딩 조끼"
                  },
                  {
                        "slot": "하의",
                        "name": "올리브 카키 와이드 카고팬츠",
                        "price": 34000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 카고 팬츠 와이드"
                  },
                  {
                        "slot": "신발",
                        "name": "아웃도어 트레킹 스니커즈",
                        "price": 49000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 아웃도어 스니커즈"
                  }
            ]
      },
      {
            "id": "M10_07",
            "mode": "male_10s",
            "title": "[남성 10대] 체크 오버핏 셔츠 & 브라운 와이드 슬랙스 룩",
            "image": "/assets/looks/male_10s/LOOK07.webp",
            "thumbnail": "/assets/looks/male_10s/LOOK07.webp",
            "totalPrice": 96000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "플란넬 오버핏 체크 긴팔 셔츠",
                        "price": 32000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 플란넬 체크 셔츠"
                  },
                  {
                        "slot": "하의",
                        "name": "브라운 루즈핏 코튼 와이드 팬츠",
                        "price": 33000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 와이드 면바지"
                  },
                  {
                        "slot": "신발",
                        "name": "클래식 캔버스 스니커즈",
                        "price": 31000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 캔버스 스니커즈"
                  }
            ]
      },
      {
            "id": "M10_08",
            "mode": "male_10s",
            "title": "[남성 10대] 그레이 레터링 맨투맨 & 조거 팬츠 룩",
            "image": "/assets/looks/male_10s/LOOK08.webp",
            "thumbnail": "/assets/looks/male_10s/LOOK08.webp",
            "totalPrice": 104000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "헤비웨이트 루즈핏 크루넥 맨투맨",
                        "price": 32000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 헤비웨이트 맨투맨"
                  },
                  {
                        "slot": "하의",
                        "name": "그레이 스웨트 조거 팬츠",
                        "price": 28000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 스웨트 조거팬츠"
                  },
                  {
                        "slot": "신발",
                        "name": "화이트 앤 실버 청키 스니커즈",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 청키 스니커즈"
                  }
            ]
      },
      {
            "id": "M10_09",
            "mode": "male_10s",
            "title": "[남성 10대] 블루 배색 바람막이 점퍼 & 트랙 팬츠 룩",
            "image": "/assets/looks/male_10s/LOOK09.webp",
            "thumbnail": "/assets/looks/male_10s/LOOK09.webp",
            "totalPrice": 118000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "스포티 배색 윈드브레이커 집업",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 배색 바람막이 점퍼"
                  },
                  {
                        "slot": "하의",
                        "name": "블랙 사이드 라인 트랙 팬츠",
                        "price": 29000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 트랙 팬츠 져지"
                  },
                  {
                        "slot": "신발",
                        "name": "스포티 러닝 슈즈",
                        "price": 43000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 스포티 러닝화"
                  }
            ]
      },
      {
            "id": "M10_10",
            "mode": "male_10s",
            "title": "[남성 10대] 베이지 워크웨어 자켓 & 와이드 진 룩",
            "image": "/assets/looks/male_10s/LOOK10.webp",
            "thumbnail": "/assets/looks/male_10s/LOOK10.webp",
            "totalPrice": 133000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "멀티 포켓 코튼 워크 자켓",
                        "price": 52000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 워크웨어 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "진청 스트레이트 와이드 데님",
                        "price": 36000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 와이드 청바지"
                  },
                  {
                        "slot": "신발",
                        "name": "볼드 러버솔 스니커즈",
                        "price": 45000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 볼드솔 스니커즈"
                  }
            ]
      }
];

    this.categories.male_30s = [
      {
            "id": "M30_01",
            "mode": "male_30s",
            "title": "[남성 30대] 네이비 테일러드 블레이저 & 베이지 치노 룩",
            "image": "/assets/looks/male_30s/LOOK01.webp",
            "thumbnail": "/assets/looks/male_30s/LOOK01.webp",
            "totalPrice": 174000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "울 블렌드 테일러드 네이비 자켓",
                        "price": 78000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 네이비 테일러드 블레이저"
                  },
                  {
                        "slot": "하의",
                        "name": "슬림 테이퍼드 베이지 치노 팬츠",
                        "price": 38000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 베이지 치노 팬츠"
                  },
                  {
                        "slot": "신발",
                        "name": "소가죽 첼시 부츠",
                        "price": 58000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 첼시부츠"
                  }
            ]
      },
      {
            "id": "M30_02",
            "mode": "male_30s",
            "title": "[남성 30대] 차콜 울 싱글 맥코트 & 생지 데님 룩",
            "image": "/assets/looks/male_30s/LOOK02.webp",
            "thumbnail": "/assets/looks/male_30s/LOOK02.webp",
            "totalPrice": 205000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "울 블렌드 싱글 발마칸 코트",
                        "price": 115000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 울 싱글 발마칸 코트"
                  },
                  {
                        "slot": "하의",
                        "name": "슬림 스트레이트 생지 데님",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 생지 일자 청바지"
                  },
                  {
                        "slot": "신발",
                        "name": "미니멀 화이트 레더 스니커즈",
                        "price": 48000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 화이트 스니커즈"
                  }
            ]
      },
      {
            "id": "M30_03",
            "mode": "male_30s",
            "title": "[남성 30대] 카멜 싱글 수트 자켓 & 네이비 슬랙스 룩",
            "image": "/assets/looks/male_30s/LOOK03.webp",
            "thumbnail": "/assets/looks/male_30s/LOOK03.webp",
            "totalPrice": 180000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "캐주얼 카멜 싱글 브레스트 자켓",
                        "price": 84000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 카멜 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "네이비 핀턱 스트레이트 슬랙스",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 네이비 핀턱 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "다크브라운 페니 로퍼",
                        "price": 54000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 소가죽 페니 로퍼"
                  }
            ]
      },
      {
            "id": "M30_04",
            "mode": "male_30s",
            "title": "[남성 30대] 올리브 필드 M-65 자켓 & 연청 데님 룩",
            "image": "/assets/looks/male_30s/LOOK04.webp",
            "thumbnail": "/assets/looks/male_30s/LOOK04.webp",
            "totalPrice": 156000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "밀리터리 필드 사파리 자켓",
                        "price": 68000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 필드 사파리 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "레귤러 스트레이트 연청 데님",
                        "price": 39000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 일자 연청바지"
                  },
                  {
                        "slot": "신발",
                        "name": "독일군 레더 스니커즈",
                        "price": 49000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 독일군 스니커즈"
                  }
            ]
      },
      {
            "id": "M30_05",
            "mode": "male_30s",
            "title": "[남성 30대] 베이지 투버튼 셋업 자켓 & 블랙 슬랙스 룩",
            "image": "/assets/looks/male_30s/LOOK05.webp",
            "thumbnail": "/assets/looks/male_30s/LOOK05.webp",
            "totalPrice": 183000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "소프트 울 셋업 테일러드 자켓",
                        "price": 88000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 캐주얼 셋업 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "블랙 테이퍼드 핏 슬랙스",
                        "price": 39000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 테이퍼드 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "블랙 더비 슈즈",
                        "price": 56000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 클래식 더비 슈즈"
                  }
            ]
      },
      {
            "id": "M30_06",
            "mode": "male_30s",
            "title": "[남성 30대] 블랙 싱글 체스터 코트 & 슬림 슬랙스 룩",
            "image": "/assets/looks/male_30s/LOOK06.webp",
            "thumbnail": "/assets/looks/male_30s/LOOK06.webp",
            "totalPrice": 220000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "핸드메이드 울 싱글 롱코트",
                        "price": 132000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 울 싱글 롱코트"
                  },
                  {
                        "slot": "하의",
                        "name": "차콜 슬림 스트레이트 슬랙스",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 슬림 정장 바지"
                  },
                  {
                        "slot": "신발",
                        "name": "미니멀 레더 스니커즈",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 미니멀 스니커즈"
                  }
            ]
      },
      {
            "id": "M30_07",
            "mode": "male_30s",
            "title": "[남성 30대] 다크그린 니트 가디건 & 그레이 슬랙스 룩",
            "image": "/assets/looks/male_30s/LOOK07.webp",
            "thumbnail": "/assets/looks/male_30s/LOOK07.webp",
            "totalPrice": 141000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "V넥 램스울 니트 가디건",
                        "price": 48000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 램스울 니트 가디건"
                  },
                  {
                        "slot": "하의",
                        "name": "소프트 그레이 핀턱 슬랙스",
                        "price": 41000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 그레이 핀턱 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "가죽 페니 로퍼",
                        "price": 52000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 로퍼"
                  }
            ]
      },
      {
            "id": "M30_08",
            "mode": "male_30s",
            "title": "[남성 30대] 네이비 MA-1 항공점퍼 & 슬랙스 룩",
            "image": "/assets/looks/male_30s/LOOK08.webp",
            "thumbnail": "/assets/looks/male_30s/LOOK08.webp",
            "totalPrice": 162000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "미니멀 헤비 MA-1 블루종 자켓",
                        "price": 64000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 MA-1 블루종 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "라이트그레이 테이퍼드 슬랙스",
                        "price": 39000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 테이퍼드 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "블랙 첼시 부츠",
                        "price": 59000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 첼시부츠"
                  }
            ]
      },
      {
            "id": "M30_09",
            "mode": "male_30s",
            "title": "[남성 30대] 글렌체크 블레이저 & 네이비 치노 룩",
            "image": "/assets/looks/male_30s/LOOK09.webp",
            "thumbnail": "/assets/looks/male_30s/LOOK09.webp",
            "totalPrice": 173000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "클래식 글렌체크 싱글 자켓",
                        "price": 89000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 체크 테일러드 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "네이비 슬림 치노 팬츠",
                        "price": 39000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 네이비 면바지"
                  },
                  {
                        "slot": "신발",
                        "name": "화이트 코트 스니커즈",
                        "price": 45000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 화이트 코트화"
                  }
            ]
      },
      {
            "id": "M30_10",
            "mode": "male_30s",
            "title": "[남성 30대] 카멜 오버 더블코트 & 블랙 테이퍼드 슬랙스 룩",
            "image": "/assets/looks/male_30s/LOOK10.webp",
            "thumbnail": "/assets/looks/male_30s/LOOK10.webp",
            "totalPrice": 245000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "울 캐시미어 더블 오버코트",
                        "price": 145000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 울 더블 롱코트"
                  },
                  {
                        "slot": "하의",
                        "name": "블랙 테이퍼드 핀턱 슬랙스",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 블랙 핀턱 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "블랙 레이스업 더비 슈즈",
                        "price": 58000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 소가죽 더비슈즈"
                  }
            ]
      }
];

    this.categories.male_40s = [
      {
            "id": "M40_01",
            "mode": "male_40s",
            "title": "[남성 40대] 다크카키 사파리 필드 자켓 & 그레이 울 슬랙스 룩",
            "image": "/assets/looks/male_40s/LOOK01.webp",
            "thumbnail": "/assets/looks/male_40s/LOOK01.webp",
            "totalPrice": 196000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "스탠드 카라 패디드 필드 자켓",
                        "price": 86000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 사파리 패딩 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "그레이 울 블렌드 핀턱 슬랙스",
                        "price": 48000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 울 핀턱 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "다크브라운 레이스업 부츠",
                        "price": 62000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 레이스업 부츠"
                  }
            ]
      },
      {
            "id": "M40_02",
            "mode": "male_40s",
            "title": "[남성 40대] 카멜 벨티드 트렌치코트 & 네이비 치노 룩",
            "image": "/assets/looks/male_40s/LOOK02.webp",
            "thumbnail": "/assets/looks/male_40s/LOOK02.webp",
            "totalPrice": 216000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "클래식 더블 트렌치 롱코트",
                        "price": 125000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 더블 트렌치코트"
                  },
                  {
                        "slot": "하의",
                        "name": "네이비 스트레이트 핏 치노",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 네이비 면바지"
                  },
                  {
                        "slot": "신발",
                        "name": "클래식 레더 화이트 스니커즈",
                        "price": 49000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 스니커즈"
                  }
            ]
      },
      {
            "id": "M40_03",
            "mode": "male_40s",
            "title": "[남성 40대] 그레이 윈도우페인 체크 자켓 & 데님 룩",
            "image": "/assets/looks/male_40s/LOOK03.webp",
            "thumbnail": "/assets/looks/male_40s/LOOK03.webp",
            "totalPrice": 199000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "울 혼방 싱글 체크 블레이저",
                        "price": 98000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 체크 싱글 블레이저"
                  },
                  {
                        "slot": "하의",
                        "name": "다크인디고 스트레이트 진",
                        "price": 45000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 일자 청바지"
                  },
                  {
                        "slot": "신발",
                        "name": "브라운 페니 로퍼",
                        "price": 56000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 소가죽 페니 로퍼"
                  }
            ]
      },
      {
            "id": "M40_04",
            "mode": "male_40s",
            "title": "[남성 40대] 아이보리 숄칼라 니트 가디건 & 베이지 슬랙스 룩",
            "image": "/assets/looks/male_40s/LOOK04.webp",
            "thumbnail": "/assets/looks/male_40s/LOOK04.webp",
            "totalPrice": 156000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "케이블 숄칼라 울 가디건",
                        "price": 68000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 숄카라 니트 가디건"
                  },
                  {
                        "slot": "하의",
                        "name": "베이지 코튼 테이퍼드 팬츠",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 베이지 테이퍼드 바지"
                  },
                  {
                        "slot": "신발",
                        "name": "스웨이드 스니커즈",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 스웨이드 스니커즈"
                  }
            ]
      },
      {
            "id": "M40_05",
            "mode": "male_40s",
            "title": "[남성 40대] 블랙 가죽 라이더 자켓 & 슬림 블랙진 룩",
            "image": "/assets/looks/male_40s/LOOK05.webp",
            "thumbnail": "/assets/looks/male_40s/LOOK05.webp",
            "totalPrice": 274000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "천연 양가죽 싱글 라이더 자켓",
                        "price": 168000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 양가죽 라이더 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "슬림핏 블랙 데님 팬츠",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 슬림 블랙진"
                  },
                  {
                        "slot": "신발",
                        "name": "소가죽 첼시 부츠",
                        "price": 64000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 첼시부츠"
                  }
            ]
      },
      {
            "id": "M40_06",
            "mode": "male_40s",
            "title": "[남성 40대] 네이비 블레이저 & 베이지 슬랙스 비즈니스 캐주얼 룩",
            "image": "/assets/looks/male_40s/LOOK06.webp",
            "thumbnail": "/assets/looks/male_40s/LOOK06.webp",
            "totalPrice": 192000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "원버튼 테일러드 네이비 블레이저",
                        "price": 88000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 네이비 정장 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "베이지 핀턱 스트레이트 슬랙스",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 베이지 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "가죽 비트 로퍼",
                        "price": 58000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 홀스빗 로퍼"
                  }
            ]
      },
      {
            "id": "M40_07",
            "mode": "male_40s",
            "title": "[남성 40대] 베이지 블루종 점퍼 & 올리브 치노 팬츠 룩",
            "image": "/assets/looks/male_40s/LOOK07.webp",
            "thumbnail": "/assets/looks/male_40s/LOOK07.webp",
            "totalPrice": 156000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "미니멀 립조직 코튼 블루종",
                        "price": 68000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 면 블루종 점퍼"
                  },
                  {
                        "slot": "하의",
                        "name": "올리브 카키 스트레이트 치노",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 카키 면바지"
                  },
                  {
                        "slot": "신발",
                        "name": "브라운 스니커즈",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 스니커즈"
                  }
            ]
      },
      {
            "id": "M40_08",
            "mode": "male_40s",
            "title": "[남성 40대] 딥그린 카라 니트 & 그레이 슬랙스 룩",
            "image": "/assets/looks/male_40s/LOOK08.webp",
            "thumbnail": "/assets/looks/male_40s/LOOK08.webp",
            "totalPrice": 154000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "파인 울 오픈카라 니트 스웨터",
                        "price": 52000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 카라 니트 스웨터"
                  },
                  {
                        "slot": "하의",
                        "name": "미디엄 그레이 스트레이트 슬랙스",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 그레이 정장 바지"
                  },
                  {
                        "slot": "신발",
                        "name": "소가죽 페니 로퍼",
                        "price": 56000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 페니 로퍼"
                  }
            ]
      },
      {
            "id": "M40_09",
            "mode": "male_40s",
            "title": "[남성 40대] 네이비 더블 피코트 & 차콜 슬랙스 룩",
            "image": "/assets/looks/male_40s/LOOK09.webp",
            "thumbnail": "/assets/looks/male_40s/LOOK09.webp",
            "totalPrice": 209000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "울 블렌드 더블 브레스트 피코트",
                        "price": 118000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 울 더블 피코트"
                  },
                  {
                        "slot": "하의",
                        "name": "차콜 테이퍼드 슬랙스",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 테이퍼드 정장 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "화이트 코트 스니커즈",
                        "price": 45000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 화이트 코트화"
                  }
            ]
      },
      {
            "id": "M40_10",
            "mode": "male_40s",
            "title": "[남성 40대] 차콜 싱글 체스터필드 코트 & 블랙 슬랙스 룩",
            "image": "/assets/looks/male_40s/LOOK10.webp",
            "thumbnail": "/assets/looks/male_40s/LOOK10.webp",
            "totalPrice": 246000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "캐시미어 블렌드 싱글 롱코트",
                        "price": 138000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 캐시미어 싱글 코트"
                  },
                  {
                        "slot": "하의",
                        "name": "블랙 스트레이트 핀턱 슬랙스",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 블랙 스트레이트 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "소가죽 레이스업 더비 슈즈",
                        "price": 62000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 더비슈즈"
                  }
            ]
      }
];

    this.categories.male_50s = [
      {
            "id": "M50_01",
            "mode": "male_50s",
            "title": "[남성 50대] 네이비 언스트럭처드 블레이저 & 베이지 팬츠 룩",
            "image": "/assets/looks/male_50s/LOOK01.webp",
            "thumbnail": "/assets/looks/male_50s/LOOK01.webp",
            "totalPrice": 179000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "경량 언컨스트럭티드 네이비 자켓",
                        "price": 89000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 경량 캐주얼 블레이저"
                  },
                  {
                        "slot": "하의",
                        "name": "베이지 코튼 릴렉스 슬랙스",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 릴렉스핏 면바지"
                  },
                  {
                        "slot": "신발",
                        "name": "클래식 화이트 가죽 스니커즈",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 화이트 스니커즈"
                  }
            ]
      },
      {
            "id": "M50_02",
            "mode": "male_50s",
            "title": "[남성 50대] 차콜 숄칼라 가디건 & 다크그레이 슬랙스 룩",
            "image": "/assets/looks/male_50s/LOOK02.webp",
            "thumbnail": "/assets/looks/male_50s/LOOK02.webp",
            "totalPrice": 168000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "울 혼방 숄칼라 립 니트 가디건",
                        "price": 68000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 숄카라 울 가디건"
                  },
                  {
                        "slot": "하의",
                        "name": "다크그레이 허리밴딩 슬랙스",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 허리밴딩 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "소가죽 페니 로퍼",
                        "price": 54000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 페니 로퍼"
                  }
            ]
      },
      {
            "id": "M50_03",
            "mode": "male_50s",
            "title": "[남성 50대] 올리브 사파리 자켓 & 아이보리 팬츠 룩",
            "image": "/assets/looks/male_50s/LOOK03.webp",
            "thumbnail": "/assets/looks/male_50s/LOOK03.webp",
            "totalPrice": 169000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "멀티 포켓 사파리 야상 자켓",
                        "price": 78000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 사파리 야상 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "아이보리 코튼 스트레이트 팬츠",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 아이보리 면바지"
                  },
                  {
                        "slot": "신발",
                        "name": "가죽 보트 슈즈",
                        "price": 49000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 보트슈즈"
                  }
            ]
      },
      {
            "id": "M50_04",
            "mode": "male_50s",
            "title": "[남성 50대] 베이지 수트 자켓 & 터틀넥 데님 룩",
            "image": "/assets/looks/male_50s/LOOK04.webp",
            "thumbnail": "/assets/looks/male_50s/LOOK04.webp",
            "totalPrice": 199000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "소프트 울 싱글 블레이저",
                        "price": 92000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 베이지 싱글 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "스트레이트 핏 다크 데님",
                        "price": 45000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 일자 청바지"
                  },
                  {
                        "slot": "신발",
                        "name": "브라운 첼시 부츠",
                        "price": 62000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 첼시부츠"
                  }
            ]
      },
      {
            "id": "M50_05",
            "mode": "male_50s",
            "title": "[남성 50대] 그레이 플란넬 셔츠 자켓 & 네이비 팬츠 룩",
            "image": "/assets/looks/male_50s/LOOK05.webp",
            "thumbnail": "/assets/looks/male_50s/LOOK05.webp",
            "totalPrice": 147000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "울 플란넬 오버핏 셔켓",
                        "price": 58000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 플란넬 셔츠 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "네이비 스트레이트 치노 팬츠",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 네이비 면바지"
                  },
                  {
                        "slot": "신발",
                        "name": "가죽 코트화 스니커즈",
                        "price": 45000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 스니커즈"
                  }
            ]
      },
      {
            "id": "M50_06",
            "mode": "male_50s",
            "title": "[남성 50대] 청록 브이넥 니트 & 브라운 치노 팬츠 룩",
            "image": "/assets/looks/male_50s/LOOK06.webp",
            "thumbnail": "/assets/looks/male_50s/LOOK06.webp",
            "totalPrice": 145000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "소프트 램스울 브이넥 스웨터",
                        "price": 49000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 브이넥 울 니트"
                  },
                  {
                        "slot": "하의",
                        "name": "브라운 스트레이트 코튼 팬츠",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 브라운 면바지"
                  },
                  {
                        "slot": "신발",
                        "name": "클래식 가죽 로퍼",
                        "price": 52000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 클래식 가죽 로퍼"
                  }
            ]
      },
      {
            "id": "M50_07",
            "mode": "male_50s",
            "title": "[남성 50대] 라이트그레이 블레이저 & 데님 팬츠 룩",
            "image": "/assets/looks/male_50s/LOOK07.webp",
            "thumbnail": "/assets/looks/male_50s/LOOK07.webp",
            "totalPrice": 174000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "투버튼 라이트 싱글 자켓",
                        "price": 84000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 캐주얼 싱글 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "레귤러 스트레이트 중청 데님",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 일자 중청바지"
                  },
                  {
                        "slot": "신발",
                        "name": "화이트 레더 스니커즈",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 스니커즈"
                  }
            ]
      },
      {
            "id": "M50_08",
            "mode": "male_50s",
            "title": "[남성 50대] 다크그린 숄칼라 니트 & 베이지 치노 룩",
            "image": "/assets/looks/male_50s/LOOK08.webp",
            "thumbnail": "/assets/looks/male_50s/LOOK08.webp",
            "totalPrice": 165000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "케이블 조직 숄칼라 가디건",
                        "price": 65000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 숄카라 니트 가디건"
                  },
                  {
                        "slot": "하의",
                        "name": "베이지 스트레이트 핏 면바지",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 베이지 일자 면바지"
                  },
                  {
                        "slot": "신발",
                        "name": "가죽 데저트 부츠",
                        "price": 58000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 스웨이드 데저트 부츠"
                  }
            ]
      },
      {
            "id": "M50_09",
            "mode": "male_50s",
            "title": "[남성 50대] 와인 해링턴 자켓 & 체크 슬랙스 룩",
            "image": "/assets/looks/male_50s/LOOK09.webp",
            "thumbnail": "/assets/looks/male_50s/LOOK09.webp",
            "totalPrice": 162000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "클래식 코튼 해링턴 블루종",
                        "price": 68000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 해링턴 블루종 점퍼"
                  },
                  {
                        "slot": "하의",
                        "name": "글렌체크 핀턱 슬랙스",
                        "price": 46000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 체크 핀턱 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "가죽 슬립온 스니커즈",
                        "price": 48000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 슬립온"
                  }
            ]
      },
      {
            "id": "M50_10",
            "mode": "male_50s",
            "title": "[남성 50대] 베이지 패딩 베스트 & 카키 카고 슬랙스 룩",
            "image": "/assets/looks/male_50s/LOOK10.webp",
            "thumbnail": "/assets/looks/male_50s/LOOK10.webp",
            "totalPrice": 152000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "스탠드넥 경량 볼륨 패딩 조끼",
                        "price": 52000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 패딩 조끼"
                  },
                  {
                        "slot": "하의",
                        "name": "카키 테이퍼드 카고 팬츠",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 테이퍼드 카고팬츠"
                  },
                  {
                        "slot": "신발",
                        "name": "가죽 아웃도어 워킹화",
                        "price": 56000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 아웃도어 워킹화"
                  }
            ]
      }
];

    this.categories.male_60s = [
      {
            "id": "M60_01",
            "mode": "male_60s",
            "title": "[남성 60대] 하운드투스 브라운 블레이저 & 차콜 슬랙스 룩",
            "image": "/assets/looks/male_60s/LOOK01.webp",
            "thumbnail": "/assets/looks/male_60s/LOOK01.webp",
            "totalPrice": 190000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "클래식 하운드투스 체크 자켓",
                        "price": 94000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "시니어 남성 체크 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "차콜 허리밴딩 컴포트 슬랙스",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 밴딩 정장 바지"
                  },
                  {
                        "slot": "신발",
                        "name": "다크브라운 컴포트 슈즈",
                        "price": 52000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 기능성 컴포트 로퍼"
                  }
            ]
      },
      {
            "id": "M60_02",
            "mode": "male_60s",
            "title": "[남성 60대] 차콜 집업 니트 스웨터 & 베이지 팬츠 룩",
            "image": "/assets/looks/male_60s/LOOK02.webp",
            "thumbnail": "/assets/looks/male_60s/LOOK02.webp",
            "totalPrice": 146000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "하이넥 울 혼방 하프집업 스웨터",
                        "price": 56000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 하프집업 니트"
                  },
                  {
                        "slot": "하의",
                        "name": "베이지 신축성 스트레이트 팬츠",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 신축성 밴딩 면바지"
                  },
                  {
                        "slot": "신발",
                        "name": "가죽 모카신 슬립온",
                        "price": 48000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 모카신"
                  }
            ]
      },
      {
            "id": "M60_03",
            "mode": "male_60s",
            "title": "[남성 60대] 올리브 패딩 베스트 & 데님 팬츠 룩",
            "image": "/assets/looks/male_60s/LOOK03.webp",
            "thumbnail": "/assets/looks/male_60s/LOOK03.webp",
            "totalPrice": 144000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "경량 스탠드넥 퀼팅 패딩 조끼",
                        "price": 48000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 경량 패딩 조끼"
                  },
                  {
                        "slot": "하의",
                        "name": "스트레이트 핏 신축 데님",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 밴딩 스판 청바지"
                  },
                  {
                        "slot": "신발",
                        "name": "아웃도어 워킹화",
                        "price": 54000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 쿠션 워킹화"
                  }
            ]
      },
      {
            "id": "M60_04",
            "mode": "male_60s",
            "title": "[남성 60대] 블랙 니트 조끼 & 셔츠 슬랙스 룩",
            "image": "/assets/looks/male_60s/LOOK04.webp",
            "thumbnail": "/assets/looks/male_60s/LOOK04.webp",
            "totalPrice": 138000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "브이넥 버튼 울 니트 베스트",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 브이넥 니트 조끼"
                  },
                  {
                        "slot": "하의",
                        "name": "차콜 스트레이트 정장 슬랙스",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 일자 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "가죽 더비 컴포트화",
                        "price": 52000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 더비슈즈"
                  }
            ]
      },
      {
            "id": "M60_05",
            "mode": "male_60s",
            "title": "[남성 60대] 카멜 사파리 필드 자켓 & 네이비 팬츠 룩",
            "image": "/assets/looks/male_60s/LOOK05.webp",
            "thumbnail": "/assets/looks/male_60s/LOOK05.webp",
            "totalPrice": 166000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "다기능 포켓 코튼 사파리 자켓",
                        "price": 76000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 사파리 자켓"
                  },
                  {
                        "slot": "하의",
                        "name": "네이비 스트레이트 코튼 팬츠",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 네이비 면바지"
                  },
                  {
                        "slot": "신발",
                        "name": "가죽 워킹 로퍼",
                        "price": 48000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 편한 가죽 로퍼"
                  }
            ]
      },
      {
            "id": "M60_06",
            "mode": "male_60s",
            "title": "[남성 60대] 브라운 노르딕 카라 니트 & 베이지 팬츠 룩",
            "image": "/assets/looks/male_60s/LOOK06.webp",
            "thumbnail": "/assets/looks/male_60s/LOOK06.webp",
            "totalPrice": 152000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "카라형 패턴 울 니트 스웨터",
                        "price": 58000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 카라 니트 스웨터"
                  },
                  {
                        "slot": "하의",
                        "name": "베이지 코듀로이 스트레이트 팬츠",
                        "price": 45000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 골덴 바지 밴딩"
                  },
                  {
                        "slot": "신발",
                        "name": "스웨이드 로퍼",
                        "price": 49000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 스웨이드 로퍼"
                  }
            ]
      },
      {
            "id": "M60_07",
            "mode": "male_60s",
            "title": "[남성 60대] 네이비 하이넥 패딩 사파리 자켓 룩",
            "image": "/assets/looks/male_60s/LOOK07.webp",
            "thumbnail": "/assets/looks/male_60s/LOOK07.webp",
            "totalPrice": 175000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "방풍 하이넥 패딩 점퍼",
                        "price": 84000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 방풍 패딩 점퍼"
                  },
                  {
                        "slot": "하의",
                        "name": "블랙 스트레이트 밴딩 바지",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 블랙 밴딩 바지"
                  },
                  {
                        "slot": "신발",
                        "name": "발편한 워킹 스니커즈",
                        "price": 49000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 발편한 워킹화"
                  }
            ]
      },
      {
            "id": "M60_08",
            "mode": "male_60s",
            "title": "[남성 60대] 네이비 싱글 블레이저 & 베이지 슬랙스 룩",
            "image": "/assets/looks/male_60s/LOOK08.webp",
            "thumbnail": "/assets/looks/male_60s/LOOK08.webp",
            "totalPrice": 184000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "클래식 투버튼 테일러드 네이비 자켓",
                        "price": 88000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 네이비 블레이저"
                  },
                  {
                        "slot": "하의",
                        "name": "베이지 스트레이트 슬랙스",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 베이지 슬랙스"
                  },
                  {
                        "slot": "신발",
                        "name": "클래식 페니 로퍼",
                        "price": 52000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 가죽 페니 로퍼"
                  }
            ]
      },
      {
            "id": "M60_09",
            "mode": "male_60s",
            "title": "[남성 60대] 다크그린 집업 니트 가디건 & 브라운 슬랙스 룩",
            "image": "/assets/looks/male_60s/LOOK09.webp",
            "thumbnail": "/assets/looks/male_60s/LOOK09.webp",
            "totalPrice": 150000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "풀집업 하이넥 울 가디건",
                        "price": 59000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 집업 가디건 니트"
                  },
                  {
                        "slot": "하의",
                        "name": "브라운 신축 밴딩 슬랙스",
                        "price": 42000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 신축성 밴딩 바지"
                  },
                  {
                        "slot": "신발",
                        "name": "가죽 컴포트화",
                        "price": 49000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 발편한 컴포트화"
                  }
            ]
      },
      {
            "id": "M60_10",
            "mode": "male_60s",
            "title": "[남성 60대] 베이지 버튼 니트 가디건 & 생지 데님 룩",
            "image": "/assets/looks/male_60s/LOOK10.webp",
            "thumbnail": "/assets/looks/male_60s/LOOK10.webp",
            "totalPrice": 154000,
            "items": [
                  {
                        "slot": "상의",
                        "name": "브이넥 포켓 울 니트 가디건",
                        "price": 56000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 포켓 니트 가디건"
                  },
                  {
                        "slot": "하의",
                        "name": "스트레이트 핏 데님 팬츠",
                        "price": 44000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 일자 밴딩 청바지"
                  },
                  {
                        "slot": "신발",
                        "name": "아웃도어 트레킹 로우",
                        "price": 54000,
                        "coupangUrl": "https://www.coupang.com",
                        "searchKeyword": "남성 트레킹화"
                  }
            ]
      }
];

    // Backward compatibility aliases
    this.categories.female = this.categories.female_20s;
    this.categories.male = this.categories.male_20s;
    this.categories.real = this.categories.female_20s;
    this.categories.male2d = this.categories.male_20s;
  }

  getLooks(mode) {
    if (this.categories[mode]) return this.categories[mode];
    if (mode === 'female' || mode === 'real') return this.categories.female_20s;
    if (mode === 'male' || mode === 'male2d') return this.categories.male_20s;
    return this.categories.female_20s;
  }

  getOutfit(mode, outfitId) {
    const list = this.getLooks(mode);
    return list.find(o => o.id === outfitId) || list[0];
  }

  getRandom(mode, excludeId = null) {
    const list = this.getLooks(mode);
    if (!list.length) return null;
    const candidates = list.filter(o => o.id !== excludeId);
    return candidates[Math.floor(Math.random() * candidates.length)] || list[0];
  }

  getGroups() {
    return DEMOGRAPHIC_GROUPS;
  }
}
