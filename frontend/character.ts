// キャラクターの進化段階に応じた見た目と、進化までの進捗計算を集約する。
// ホーム画面のほか、将来マップの現在地マーカーでも同じ絵を使えるようにする。

// バックエンド(character.py)の EVOLUTION_LEVELS と対応させる。
// この境界レベルに到達すると evolution_stage が 1 つ上がる。
export const EVOLUTION_LEVELS = [10, 30, 60, 100] as const;

export interface CharacterAppearance {
    // 表示する画像のパス。
    src: string;
    // 静止画(PNG)は true。CSSで「ぴょこぴょこ」動かす。GIFは自分で動くので false。
    bounce: boolean;
}

// 進化段階 0〜4 に対応する見た目。
// 進化前(stage 0)は SD の静止画をぴょこぴょこ、進化後(stage>=1)は動くGIFをそのまま。
// 素材が増えたらここに段階ごとの画像を足すだけでよい。
const APPEARANCE_BY_STAGE: readonly CharacterAppearance[] = [
    { src: "images/deformed.png", bounce: true },
    { src: "images/characterGIF.gif", bounce: false },
    { src: "images/characterGIF.gif", bounce: false },
    { src: "images/characterGIF.gif", bounce: false },
    { src: "images/characterGIF.gif", bounce: false },
];

// 進化段階から表示する見た目を返す。未知の段階は最終段階に丸める。
export function appearanceForStage(stage: number): CharacterAppearance {
    const index = Math.min(
        Math.max(stage, 0),
        APPEARANCE_BY_STAGE.length - 1,
    );
    return APPEARANCE_BY_STAGE[index];
}

export interface EvolutionProgress {
    // 現段階の中で次の進化までどれだけ進んだか（0〜1）。
    ratio: number;
    // 次に進化するレベル。最終段階なら null。
    nextLevel: number | null;
}

// 現在レベルと進化段階から、次の進化までの進捗を計算する。
export function evolutionProgress(
    level: number,
    stage: number,
): EvolutionProgress {
    // 最終段階（stage 4 = レベル100到達）はこれ以上進化しない。
    if (stage >= EVOLUTION_LEVELS.length) {
        return { ratio: 1, nextLevel: null };
    }

    const nextLevel = EVOLUTION_LEVELS[stage];
    const lowerLevel = stage === 0 ? 1 : EVOLUTION_LEVELS[stage - 1];
    const span = nextLevel - lowerLevel;
    const ratio = span <= 0 ? 1 : (level - lowerLevel) / span;

    return {
        ratio: Math.min(Math.max(ratio, 0), 1),
        nextLevel,
    };
}
