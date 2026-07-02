/**
 * Rev21 vs antichrist_666 routing smoke.
 * Run: npx tsx scripts/smoke-logos-inquiry-verse-thematic-v1.ts
 */
import {
  detectAntichrist666Topic,
  detectRev21NewCreationTopic,
  parseRevelationChapterFromQuery,
} from "../src/lib/logosInquiryVerseThematicV1.ts";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

const rev21 = "요한계시록 21장 새 하늘과 새 땅의 상징은?";
assert(parseRevelationChapterFromQuery(rev21) === 21, "rev21 chapter parse");
assert(detectRev21NewCreationTopic(rev21), "rev21 topic");
assert(!detectAntichrist666Topic(rev21), "rev21 must not match antichrist");

const antichrist = "성경에 666 악마의 숫자, 적그리스도에 대해 궁금해";
assert(detectAntichrist666Topic(antichrist), "666 query still antichrist");

const rev13 = "요한계시록 13장 666 짐승의 숫자";
assert(parseRevelationChapterFromQuery(rev13) === 13, "rev13 chapter");
assert(detectAntichrist666Topic(rev13), "rev13 666 still antichrist");

console.log("[smoke-logos-inquiry-verse-thematic-v1] passed.");
