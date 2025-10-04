import aiohttp
import random
import asyncio
import sqlite3
from datetime import datetime, timedelta
from discord import ui, ButtonStyle
from translate import Translator
from collections import defaultdict
from config import DATABASE
import sqlite3
from datetime import datetime
from config import DATABASE 
import os
import cv2
#---------------------------- BAN ------------------------------------------------------------
# İcazə verilmiş domenlər
allowed_domains = ["youtube.com"]
warnings = {}
# ----------------------QUIZ---------------------------------------------------
questions = {
    'adın ne?': "Ben süper havalı bir botum ve amacım size yardım etmek!",
    'kaç yaşındasın?': "Bu çok felsefi bir soru..."
}

# ------------------------------TRANSLATE-------------------------------------------
class TextAnalysis:
    memory = defaultdict(list)

    def __init__(self, text, owner):
        TextAnalysis.memory[owner].append(self)
        self.text = text
        self.translation = self.__translate(self.text, "az", "en")

        if self.text in questions:
            self.response = questions[self.text]
        else:
            self.response = self.get_answer()

    def get_answer(self):
        return self.__translate("I don't know how to help", "en", "az")

    def __translate(self, text, from_lang, to_lang):
        try:
            cevirici = Translator(from_lang=from_lang, to_lang=to_lang)
            return cevirici.translate(text)
        except:
            return "Çeviri girişimi başarısız oldu"

# -------------------------QUIZ------------------------------------------------
class Question:
    def __init__(self, text, answer_id, *options):
        self.__text = text
        self.__answer_id = answer_id
        self.options = options

    @property
    def text(self):
        return self.__text

    def gen_buttons(self):
        buttons = []
        for i, option in enumerate(self.options):
            if i == self.__answer_id:
                buttons.append(ui.Button(label=option, style=ButtonStyle.primary, custom_id=f"correct_{i}"))
            else:
                buttons.append(ui.Button(label=option, style=ButtonStyle.primary, custom_id=f"wrong_{i}"))
        return buttons


quiz_questions = [
    Question("Azerbaycanin paytaxti haradir", 1, "Küba", "Bakü"),
    Question("Hansi olke Asiada yerlesir", 0, "Azerbaycan", "ABD", "Almanya"),
]

# -----------------------POKEMON--------------------------------------------------
class Pokemon:
    pokemons = {}

    def __init__(self, pokemon_trainer):
        self.pokemon_trainer = pokemon_trainer
        self.pokemon_number = random.randint(1, 1000)
        self.name = None
        self.weight = None
        self.height = None
        self.hp = random.randint(70, 100)
        self.power = random.randint(30, 60)
        self.last_feed_time = datetime.now()
        Pokemon.pokemons[pokemon_trainer] = self

    async def get_name(self):
        url = f'https://pokeapi.co/api/v2/pokemon/{self.pokemon_number}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['forms'][0]['name']
                return "Pikachu"

    async def load_data(self):
        url = f'https://pokeapi.co/api/v2/pokemon/{self.pokemon_number}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    self.height = data["height"]
                    self.weight = data["weight"]

    async def infopokemon(self):
        if not self.name:
            self.name = await self.get_name()
        if not self.height or not self.weight:
            await self.load_data()
        return (
            f"Pokémonunuzun ismi: {self.name}\n"
            f"Pokemonun boyu: {self.height/10} metre\n"
            f"Pokemonun kilosu: {self.weight/10} kilogram\n"
            f"Pokemonun sağlığı: {self.hp}\n"
            f"Pokemonun gücü: {self.power}"
        )

    async def show_img(self):
        url = f'https://pokeapi.co/api/v2/pokemon/{self.pokemon_number}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["sprites"]["front_default"]
                return None

    async def attack(self, enemy):
        if isinstance(enemy, Wizard):
            if random.randint(1, 3) == 1:
                return "Sihirbaz kalkan kullandı..."
        if enemy.hp > self.power:
            enemy.hp -= self.power
            return f"@{self.pokemon_trainer} @{enemy.pokemon_trainer}'a saldırdı...\nŞuanda düşman sağlığı: {enemy.hp}"
        else:
            enemy.hp = 0
            return f"@{self.pokemon_trainer} @{enemy.pokemon_trainer}'ı yendi..."

    async def feed(self, feed_interval=20, hp_increase=10):
        current_time = datetime.now()
        delta_time = timedelta(seconds=feed_interval)
        if (current_time - self.last_feed_time) > delta_time:
            self.hp += hp_increase
            self.last_feed_time = current_time
            return f"Pokémon sağlığı geri yüklendi. Mevcut HP: {self.hp}"
        else:
            return f"Pokémonunuzu şu zaman besleyebilirsiniz: {self.last_feed_time + delta_time}"

class Wizard(Pokemon):
    async def attack(self, enemy):
        magic_power = random.randint(5, 14)
        self.power += magic_power
        result = await super().attack(enemy)
        self.power -= magic_power
        return result + f"\nSihirbaz büyülü bir saldırı yaptı, ekstra büyü gücü: {magic_power}"

    async def feed(self):
        return await super().feed(hp_increase=5)

class Fighter(Pokemon):
    async def attack(self, enemy):
        super_power = random.randint(3, 19)
        self.power += super_power
        result = await super().attack(enemy)
        self.power -= super_power
        return result + f"\nDövüşçü ekstra güç kullandı: {super_power}"

    async def feed(self):
        return await super().feed(feed_interval=35)

async def main():
    wizard = Wizard("ali")
    fighter = Fighter("veli")

    print(await wizard.infopokemon())
    print()
    print(await fighter.infopokemon())
    print()
    print(await fighter.attack(wizard))

#---------------------------VERI TABANI---------------------------------------------------------------------------------------------------------------------------------

# Tuplelar
skills = [(_,) for _ in (['Python', 'SQL', 'API', 'Discord'])]
statuses = [(_,) for _ in (['Prototip Oluşturma', 'Geliştirme Aşamasında', 'Tamamlandı', 'Güncellendi'])]

# DB_Manager sınıfı
class DB_Manager:
    def __init__(self, database):
        self.database = database
        self.create_tables()  # Tabloları başlat

    # Tabloları oluştur
    def create_tables(self):
        conn = sqlite3.connect(self.database)
        with conn:
            # 4 önceki tablo
            conn.execute('''CREATE TABLE IF NOT EXISTS projects (
                                project_id INTEGER PRIMARY KEY,
                                user_id INTEGER,
                                project_name TEXT NOT NULL,
                                description TEXT,
                                url TEXT,
                                status_id INTEGER,
                                FOREIGN KEY(status_id) REFERENCES status(status_id)
                            )''') 
            conn.execute('''CREATE TABLE IF NOT EXISTS skills (
                                skill_id INTEGER PRIMARY KEY,
                                skill_name TEXT
                            )''')
            conn.execute('''CREATE TABLE IF NOT EXISTS project_skills (
                                project_id INTEGER,
                                skill_id INTEGER,
                                FOREIGN KEY(project_id) REFERENCES projects(project_id),
                                FOREIGN KEY(skill_id) REFERENCES skills(skill_id)
                            )''')
            conn.execute('''CREATE TABLE IF NOT EXISTS status (
                                status_id INTEGER PRIMARY KEY,
                                status_name TEXT
                            )''')
            
            # Profil tablosu
            conn.execute('''CREATE TABLE IF NOT EXISTS users (
                                user_id INTEGER PRIMARY KEY,
                                user_name TEXT
                            )''')

            conn.execute('''CREATE TABLE IF NOT EXISTS prizes (
                        prize_id INTEGER PRIMARY KEY,
                        image TEXT,
                        used INTEGER DEFAULT 0
            
                            )''')

            conn.execute('''CREATE TABLE IF NOT EXISTS winners (
                        user_id INTEGER,
                        prize_id INTEGER,
                        win_time TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(user_id),
                        FOREIGN KEY(prize_id) REFERENCES prizes(prize_id)
            
        )''')
            conn.commit()
        print("Veritabanı başarıyla oluşturuldu.")


#------------------------------------------ACIK ARTIRMA----------------------------------------------------------------------------------------------------------
    def add_user(self, user_id, user_name):
            conn = sqlite3.connect(self.database)
            with conn:
                conn.execute('INSERT INTO users VALUES (?, ?)', (user_id, user_name))
                conn.commit()

    def add_prize(self, data):
            conn = sqlite3.connect(self.database)
            with conn:
                conn.executemany('''INSERT INTO prizes (image) VALUES (?)''', data)
                conn.commit()

    def add_winner(self, user_id, prize_id):
            win_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn = sqlite3.connect(self.database)
            with conn:
                cur = conn.cursor() 
                cur.execute("SELECT * FROM winners WHERE user_id = ? AND prize_id = ?", (user_id, prize_id))
                if cur.fetchall():
                    return 0
                else:
                    conn.execute('''INSERT INTO winners (user_id, prize_id, win_time) VALUES (?, ?, ?)''', (user_id, prize_id, win_time))
                    conn.commit()
                    return 1

    
    def mark_prize_used(self, prize_id):
            conn = sqlite3.connect(self.database)
            with conn:
                conn.execute('''UPDATE prizes SET used = 1 WHERE prize_id = ?''', (prize_id,))
                conn.commit()


    def get_users(self):
            conn = sqlite3.connect(self.database)
            with conn:
                cur = conn.cursor()
                cur.execute('SELECT * FROM users')
                return [x[0] for x in cur.fetchall()] 
                
    def get_random_prize(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM prizes WHERE used = 0 ORDER BY RANDOM()')
            row = cur.fetchone()    # fetchone() zaten tek satır getirir
            return row  # Hiç sonuç yoksa None döner

            
    def get_prize_img(self, prize_id):
            conn = sqlite3.connect(self.database)
            with conn:
                cur = conn.cursor()
                cur.execute('SELECT image FROM prizes WHERE prize_id = ?', (prize_id, ))
                return cur.fetchall()[0][0]
            
    def get_winners_count(self, prize_id):
            conn = sqlite3.connect(self.database)
            with conn:
                cur = conn.cursor()
                cur.execute('SELECT COUNT(*) FROM winners WHERE prize_id = ?', (prize_id, ))
                return cur.fetchall()[0][0]
        
    def get_winners_img(self, user_id):
            conn = sqlite3.connect(self.database)
            with conn:
                cur = conn.cursor()
                cur.execute(''' 
    SELECT image FROM winners 
    INNER JOIN prizes ON 
    winners.prize_id = prizes.prize_id
    WHERE user_id = ?''', (user_id, ))
                return cur.fetchall()
            
    def get_rating(self):
            conn = sqlite3.connect(self.database)
            with conn:
                cur = conn.cursor()
                cur.execute('''
    SELECT users.user_name, COUNT(winners.prize_id) as count_prize FROM winners
    INNER JOIN users on users.user_id = winners.user_id
    GROUP BY winners.user_id
    ORDER BY count_prize
    LIMIT 10''')
                return cur.fetchall()
            


    def hide_img(self, img_name):
        image = cv2.imread(f'img/{img_name}')
        blurred_image = cv2.GaussianBlur(image, (15, 15), 0)
        pixelated_image = cv2.resize(blurred_image, (30, 30), interpolation=cv2.INTER_NEAREST)
        pixelated_image = cv2.resize(pixelated_image, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
        cv2.imwrite(f'hidden_img/{img_name}', pixelated_image)

#--------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Genel yardımcı metodlar
    def __executemany(self, sql, data):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.executemany(sql, data)
            conn.commit()

    def __select_data(self, sql, data=tuple()):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute(sql, data)
            return cur.fetchall()

    # Default insert
    def default_insert(self):
        self.__executemany('INSERT OR IGNORE INTO skills (skill_name) VALUES(?)', skills)
        self.__executemany('INSERT OR IGNORE INTO status (status_name) VALUES(?)', statuses)

    # Project işlemleri
    def insert_project(self, data):
        self.__executemany('INSERT OR IGNORE INTO projects (user_id, project_name, url, status_id) VALUES (?, ?, ?, ?)', data)

    def insert_skill(self, user_id, project_name, skill):
        project_id = self.__select_data('SELECT project_id FROM projects WHERE project_name = ? AND user_id = ?', (project_name, user_id))[0][0]
        skill_id = self.__select_data('SELECT skill_id FROM skills WHERE skill_name = ?', (skill,))[0][0]
        self.__executemany('INSERT OR IGNORE INTO project_skills VALUES (?, ?)', [(project_id, skill_id)])

    def get_statuses(self):
        return self.__select_data('SELECT status_name FROM status')

    def get_status_id(self, status_name):
        res = self.__select_data('SELECT status_id FROM status WHERE status_name = ?', (status_name,))
        return res[0][0] if res else None

    def get_projects(self, user_id):
        return self.__select_data('SELECT * FROM projects WHERE user_id = ?', (user_id,))

    def get_project_id(self, project_name, user_id):
        return self.__select_data('SELECT project_id FROM projects WHERE project_name = ? AND user_id = ?', (project_name, user_id))[0][0]

    def get_skills(self):
        return self.__select_data('SELECT * FROM skills')

    def get_project_skills(self, project_name):
        res = self.__select_data('''SELECT skill_name FROM projects 
JOIN project_skills ON projects.project_id = project_skills.project_id 
JOIN skills ON skills.skill_id = project_skills.skill_id 
WHERE project_name = ?''', (project_name,))
        return ', '.join([x[0] for x in res])

    def get_project_info(self, user_id, project_name):
        sql = '''
        SELECT project_name, description, url, status_name FROM projects 
        JOIN status ON status.status_id = projects.status_id
        WHERE project_name=? AND user_id=?'''
        return self.__select_data(sql, (project_name, user_id))

    def update_projects(self, param, data):
        self.__executemany(f"UPDATE projects SET {param} = ? WHERE project_name = ? AND user_id = ?", [data])

    def delete_project(self, user_id, project_id):
        self.__executemany("DELETE FROM projects WHERE user_id = ? AND project_id = ?", [(user_id, project_id)])

    def delete_skill(self, project_id, skill_id):
        self.__executemany("DELETE FROM skills WHERE skill_id = ? AND project_id = ?", [(skill_id, project_id)])

    # Profil işlemleri
    def insert_profile(self, user_id, ad, soyad, dogum_tarixi):
        self.__executemany('INSERT OR REPLACE INTO profil (user_id, ad, soyad, dogum_tarixi) VALUES (?, ?, ?, ?)',
                           [(user_id, ad, soyad, dogum_tarixi)])

    def get_profile(self, user_id):
        res = self.__select_data('SELECT ad, soyad, dogum_tarixi FROM profil WHERE user_id = ?', (user_id,))
        return res[0] if res else None

    def delete_profile(self, user_id):
        self.__executemany('DELETE FROM profil WHERE user_id = ?', [(user_id,)])


#-------------Dosya doğrudan çalıştırılırsa-------------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    manager = DB_Manager(DATABASE)
    manager.default_insert() 
    asyncio.run(main())
    manager.create_tables()
    prizes_img = os.listdir('img')
    data = [(x,) for x in prizes_img]
    manager.add_prize(data)