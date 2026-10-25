# 用户原始代码，逐字保留
class DigestiveSystem:
    def __init__(self, brain):
        self.brain = brain
        
    def mouth_chew(self, raw_html):
        print("👄 [嘴巴] 开始咀嚼原始数据...")
        import re
        clean_text = re.sub(r'<[^>]+>', '', raw_html) 
        chunks = clean_text.split("。")
        print(f"👄 [嘴巴] 咀嚼完成，吐下 {len(chunks)} 个数据块。")
        return chunks

    def stomach_digest(self, chunks):
        print("🫃 [胃部] 开始分泌胃酸（过滤引擎）...")
        valid_nutrition = []
        waste = []
        
        for chunk in chunks:
            if "彩票" in chunk or "骗局" in chunk or len(chunk) < 5:
                waste.append(chunk)
            else:
                valid_nutrition.append(chunk)
                
        print(f"🫃 [胃部] 消化完成。真情报：{len(valid_nutrition)} 条，垃圾：{len(waste)} 条。")
        return valid_nutrition, waste

    def intestine_absorb(self, valid_nutrition):
        print("🩸 [肠道] 开始吸收营养，固化记忆链...")
        for food in valid_nutrition:
            self.brain._write_hash(f"吸收情报: {food}")
            self.brain.energy_b += 5.0

    def excrete(self, waste):
        print(f"💩 [排泄] 将 {len(waste)} 条垃圾数据彻底排出系统。")
