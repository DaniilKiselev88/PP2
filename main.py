from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker
import folium
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Проверка и создание папок/файлов
if not os.path.exists("templates"):
    os.makedirs("templates")
if not os.path.isfile("templates/map.html"):
    with open("templates/map.html", "w", encoding="utf-8") as f:
        f.write("")

# Настройка БД с таймаутом
SQLALCHEMY_DATABASE_URL = "sqlite:///./points.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False  # Отключить логирование SQL-запросов в консоль
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Point(Base):
    __tablename__ = "points"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    description = Column(String)

# Создание таблиц
Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def show_map(request: Request):
    logger.info("Начало загрузки карты")
    try:
        db = next(get_db())
        logger.info("Подключение к БД установлено")

        # Получаем точки с ограничением количества для быстрой загрузки
        points = db.query(Point).limit(100).all()  # Ограничение до 100 точек
        logger.info(f"Получено {len(points)} точек из БД")

        # Расчёт центра карты
        if points:
            avg_lat = sum(p.latitude for p in points) / len(points)
            avg_lon = sum(p.longitude for p in points) / len(points)
        else:
            avg_lat, avg_lon = 55.7558, 37.6173  # Москва по умолчанию

        logger.info(f"Центр карты: {avg_lat}, {avg_lon}")

        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=10)

        # Добавление точек на карту с проверкой координат
        added_points = 0
        for point in points:
            # Проверка корректности координат
            if -90 <= point.latitude <= 90 and -180 <= point.longitude <= 180:
                folium.Marker(
                    location=[point.latitude, point.longitude],
            popup=f"<b>{point.name}</b><br>{point.description}",
            tooltip=point.name
        ).add_to(m)
        added_points += 1

        logger.info(f"Добавлено {added_points} маркеров на карту")

        map_html = m._repr_html_()
        logger.info("HTML карты сгенерирован")

        return templates.TemplateResponse("map.html", {
            "request": request,
            "map": map_html
        })
    except Exception as e:
        logger.error(f"Ошибка в show_map: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки карты")

@app.post("/add_point")
async def add_point(name: str, latitude: float, longitude: float, description: str = ""):
    try:
        # Валидация координат
        if not (-90 <= latitude <= 90):
            raise HTTPException(status_code=400, detail="Широта должна быть от -90 до 90")
        if not (-180 <= longitude <= 180):
            raise HTTPException(status_code=400, detail="Долгота должна быть от -180 до 180")

        db = next(get_db())
        new_point = Point(name=name, latitude=latitude, longitude=longitude, description=description)
        db.add(new_point)
        db.commit()
        db.refresh(new_point)
        return {"status": "success", "id": new_point.id}
    except Exception as e:
        logger.error(f"Ошибка добавления точки: {e}")
        raise HTTPException(status_code=500, detail="Ошибка добавления точки")
