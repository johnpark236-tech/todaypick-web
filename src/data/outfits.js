// Outfit catalog service with accurate clothing remapping and simplified gender modes (female / male)
// Retains backward compatibility while completely aligning items to actual character visuals.

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

export class OutfitManager {
  constructor() {
    this.categories = {
      female: [],
      male: []
    };
    this.init();
  }

  init() {
    // 1. Female looks (utilizing canonical Real look images)
    this.categories.female = FEMALE_LOOKS.map(look => {
      const totalPrice = look.items.reduce((acc, it) => acc + it.price, 0);
      return {
        id: look.id,
        mode: 'female',
        title: look.title,
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

    // 2. Male looks (utilizing canonical 2D Male look images)
    this.categories.male = MALE_LOOKS.map(look => {
      const totalPrice = look.items.reduce((acc, it) => acc + it.price, 0);
      return {
        id: look.id,
        mode: 'male',
        title: look.title,
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

    // Backward compatibility aliases
    this.categories.real = this.categories.female;
    this.categories.male2d = this.categories.male;
  }

  getLooks(mode) {
    if (mode === 'female' || mode === 'real') return this.categories.female;
    if (mode === 'male' || mode === 'male2d') return this.categories.male;
    return this.categories.female;
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
}
