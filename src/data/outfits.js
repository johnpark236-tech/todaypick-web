// Outfit catalog service for Real, Female 2D, and Male 2D looks
import curated2dData from './curated_2d_looks.json';
import itemsData from './items.json';
import coupangData from './coupang.json';
import realManifestData from './real_looks_manifest.json';

const itemsMap = new Map((itemsData.items || []).map(it => [it.id, it]));

export class OutfitManager {
  constructor() {
    this.categories = {
      real: [],
      female2d: [],
      male2d: []
    };
    this.init();
  }

  init() {
    // 1. Real looks (LOOK000001 - LOOK000014)
    const realLooks = [];
    for (let i = 1; i <= 14; i++) {
      const lookId = `LOOK${String(i).padStart(6, '0')}`;
      const entry = realManifestData[lookId];
      const recipe = entry?.recipe || { top: 'TOP-0001', bottom: 'BOT-0001', shoes: 'SHO-0001' };
      
      const topItem = itemsMap.get(recipe.top) || { id: recipe.top, name: '탑 아이템', slot: 'top' };
      const botItem = itemsMap.get(recipe.bottom) || { id: recipe.bottom, name: '바텀 아이템', slot: 'bottom' };
      const shoItem = itemsMap.get(recipe.shoes) || { id: recipe.shoes, name: '슈즈 아이템', slot: 'shoes' };

      const topCoupang = coupangData[recipe.top] || {};
      const botCoupang = coupangData[recipe.bottom] || {};
      const shoCoupang = coupangData[recipe.shoes] || {};

      const items = [
        {
          slot: '상의',
          name: topItem.name,
          price: topCoupang.price || 19900,
          coupangUrl: topCoupang.affiliateUrl || topCoupang.productUrl || 'https://www.coupang.com/vp/products/9686229724',
          searchKeyword: topItem.coupangKeyword || `여성 ${topItem.name}`
        },
        {
          slot: '하의',
          name: botItem.name,
          price: botCoupang.price || 24900,
          coupangUrl: botCoupang.affiliateUrl || botCoupang.productUrl || 'https://www.coupang.com/vp/products/9608996999',
          searchKeyword: botItem.coupangKeyword || `여성 ${botItem.name}`
        },
        {
          slot: '신발',
          name: shoItem.name,
          price: shoCoupang.price || 32000,
          coupangUrl: shoCoupang.affiliateUrl || shoCoupang.productUrl || 'https://www.coupang.com/vp/products/9685980738',
          searchKeyword: shoItem.coupangKeyword || `여성 ${shoItem.name}`
        }
      ];

      const totalPrice = items.reduce((acc, it) => acc + it.price, 0);

      realLooks.push({
        id: lookId,
        mode: 'real',
        title: `실사 데일리 룩 ${String(i).padStart(2, '0')}`,
        image: `/assets/looks/real/${lookId}.jpg`,
        thumbnail: `/assets/looks/real/${lookId}.jpg`,
        totalPrice,
        items
      });
    }
    this.categories.real = realLooks;

    // 2. Female 2D looks (F2D_LOOK000001 - F2D_LOOK000014)
    const f2dLooks = (curated2dData.looks || [])
      .filter(l => l.mode === 'female_2d')
      .slice(0, 14)
      .map((l, idx) => {
        const topPrice = 18900 + (idx * 900) % 7000;
        const botPrice = 22000 + (idx * 1100) % 9000;
        const shoPrice = 28000 + (idx * 1500) % 8000;
        const items = [
          {
            slot: '상의',
            name: l.topName || '여성 상의',
            price: topPrice,
            coupangUrl: 'https://www.coupang.com/vp/products/9686229724',
            searchKeyword: l.topCoupangKeyword || `여성 ${l.topName}`
          },
          {
            slot: '하의',
            name: l.bottomName || '여성 하의',
            price: botPrice,
            coupangUrl: 'https://www.coupang.com/vp/products/9608996999',
            searchKeyword: l.bottomCoupangKeyword || `여성 ${l.bottomName}`
          },
          {
            slot: '신발',
            name: l.shoesName || '여성 신발',
            price: shoPrice,
            coupangUrl: 'https://www.coupang.com/vp/products/9685980738',
            searchKeyword: l.shoesCoupangKeyword || `여성 ${l.shoesName}`
          }
        ];
        return {
          id: l.id,
          mode: 'female2d',
          title: `2D 여성 추천 룩 ${String(idx + 1).padStart(2, '0')}`,
          image: `/assets/looks/female2d/${l.id}.webp`,
          thumbnail: `/assets/looks/female2d/${l.id}.webp`,
          totalPrice: topPrice + botPrice + shoPrice,
          items
        };
      });
    this.categories.female2d = f2dLooks;

    // 3. Male 2D looks (M2D_LOOK000001 - M2D_LOOK000014)
    const m2dLooks = (curated2dData.looks || [])
      .filter(l => l.mode === 'male_2d')
      .slice(0, 14)
      .map((l, idx) => {
        const topPrice = 21000 + (idx * 1000) % 8000;
        const botPrice = 26000 + (idx * 1200) % 10000;
        const shoPrice = 34000 + (idx * 1400) % 9000;
        const items = [
          {
            slot: '상의',
            name: l.topName || '남성 상의',
            price: topPrice,
            coupangUrl: 'https://www.coupang.com/vp/products/9686229724',
            searchKeyword: l.topCoupangKeyword || `남성 ${l.topName}`
          },
          {
            slot: '하의',
            name: l.bottomName || '남성 하의',
            price: botPrice,
            coupangUrl: 'https://www.coupang.com/vp/products/9608996999',
            searchKeyword: l.bottomCoupangKeyword || `남성 ${l.bottomName}`
          },
          {
            slot: '신발',
            name: l.shoesName || '남성 신발',
            price: shoPrice,
            coupangUrl: 'https://www.coupang.com/vp/products/9685980738',
            searchKeyword: l.shoesCoupangKeyword || `남성 ${l.shoesName}`
          }
        ];
        return {
          id: l.id,
          mode: 'male2d',
          title: `2D 남성 추천 룩 ${String(idx + 1).padStart(2, '0')}`,
          image: `/assets/looks/male2d/${l.id}.webp`,
          thumbnail: `/assets/looks/male2d/${l.id}.webp`,
          totalPrice: topPrice + botPrice + shoPrice,
          items
        };
      });
    this.categories.male2d = m2dLooks;
  }

  getLooks(mode) {
    return this.categories[mode] || this.categories.real;
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
