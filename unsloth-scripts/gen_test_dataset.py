#!/usr/bin/env python3
"""Generate a small test dataset of 2000 Q&A samples for fine-tuning smoke tests."""

import json
import random

random.seed(42)

elements = [
    ("Gold", "Au"), ("Silver", "Ag"), ("Iron", "Fe"), ("Oxygen", "O"),
    ("Carbon", "C"), ("Hydrogen", "H"), ("Nitrogen", "N"), ("Copper", "Cu"),
    ("Sodium", "Na"), ("Potassium", "K"), ("Calcium", "Ca"), ("Helium", "He"),
]

planets = [
    ("red", "Mars"), ("blue", "Neptune"), ("ringed", "Saturn"),
    ("largest", "Jupiter"), ("closest to the Sun", "Mercury"),
    ("brightest", "Venus"), ("tilted", "Uranus"),
]

capitals = [
    ("France", "Paris"), ("Germany", "Berlin"), ("Japan", "Tokyo"),
    ("Brazil", "Brasilia"), ("Australia", "Canberra"), ("Canada", "Ottawa"),
    ("India", "New Delhi"), ("China", "Beijing"), ("Russia", "Moscow"),
    ("Argentina", "Buenos Aires"), ("Egypt", "Cairo"), ("Mexico", "Mexico City"),
    ("South Africa", "Pretoria"), ("Nigeria", "Abuja"), ("South Korea", "Seoul"),
    ("Turkey", "Ankara"), ("Saudi Arabia", "Riyadh"), ("Italy", "Rome"),
    ("Spain", "Madrid"), ("Portugal", "Lisbon"), ("Greece", "Athens"),
    ("Poland", "Warsaw"), ("Sweden", "Stockholm"), ("Norway", "Oslo"),
    ("Denmark", "Copenhagen"), ("Netherlands", "Amsterdam"), ("Belgium", "Brussels"),
    ("Switzerland", "Bern"), ("Austria", "Vienna"), ("Ukraine", "Kyiv"),
]

primes = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47}
squares = [(i * i, i) for i in range(2, 16)]

static_qa = [
    # Science
    ("What is photosynthesis?",
     "Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to produce oxygen and energy in the form of glucose."),
    ("What is Newton's first law of motion?",
     "Newton's first law states that an object at rest stays at rest, and an object in motion stays in motion, unless acted upon by an external force."),
    ("What is DNA?",
     "DNA (Deoxyribonucleic acid) is a molecule that carries the genetic instructions for the development, functioning, growth, and reproduction of all known organisms."),
    ("What is the difference between mitosis and meiosis?",
     "Mitosis produces two identical daughter cells for growth and repair, while meiosis produces four genetically diverse gametes for sexual reproduction."),
    ("What is an atom?",
     "An atom is the smallest unit of matter that retains the properties of an element, consisting of a nucleus (protons and neutrons) surrounded by electrons."),
    ("What is the speed of light?",
     "The speed of light in a vacuum is approximately 299,792,458 meters per second (about 3 x 10^8 m/s)."),
    ("What is gravity?",
     "Gravity is a fundamental force of nature that attracts objects with mass toward one another. On Earth, it gives weight to physical objects and causes them to fall when dropped."),
    ("What is the periodic table?",
     "The periodic table is a tabular arrangement of chemical elements ordered by atomic number, electron configuration, and recurring chemical properties."),
    # Technology
    ("What is the Internet?",
     "The Internet is a global network of interconnected computers that communicate using standardized protocols, enabling the sharing of information and services worldwide."),
    ("What is artificial intelligence?",
     "Artificial intelligence (AI) is the simulation of human intelligence processes by machines, including learning, reasoning, problem-solving, perception, and language understanding."),
    ("What is machine learning?",
     "Machine learning is a subset of AI where systems learn from data to improve their performance on tasks without being explicitly programmed."),
    ("What is a neural network?",
     "A neural network is a computational model inspired by the human brain, consisting of interconnected layers of nodes that learn to recognize patterns from data."),
    ("What is cloud computing?",
     "Cloud computing is the delivery of computing services like storage, processing, and software over the internet, allowing on-demand access without local infrastructure."),
    ("What is an operating system?",
     "An operating system (OS) is system software that manages hardware and software resources, providing services for programs. Examples include Windows, Linux, and macOS."),
    ("What is open source software?",
     "Open source software is software whose source code is publicly available for anyone to view, modify, and distribute, fostering collaboration and transparency."),
    ("What is a CPU?",
     "A CPU (Central Processing Unit) is the primary component of a computer that executes instructions, performing arithmetic, logic, control, and input/output operations."),
    ("What is the difference between RAM and ROM?",
     "RAM (Random Access Memory) is volatile memory used for temporary data storage during operation, while ROM (Read-Only Memory) is non-volatile and stores permanent firmware."),
    ("What is cybersecurity?",
     "Cybersecurity is the practice of protecting systems, networks, and programs from digital attacks, unauthorized access, and data breaches."),
    ("What is an algorithm?",
     "An algorithm is a step-by-step set of instructions or rules designed to solve a problem or accomplish a task, forming the basis of all computer programs."),
    ("What is a database?",
     "A database is an organized collection of structured data stored electronically, managed by a database management system (DBMS) for efficient retrieval and manipulation."),
    ("What is the difference between Python and Java?",
     "Python is an interpreted, dynamically-typed language known for simplicity and data science use, while Java is a compiled, statically-typed language known for portability and enterprise applications."),
    ("What is version control?",
     "Version control is a system that records changes to files over time, allowing teams to track history, collaborate, and revert to previous versions. Git is the most popular example."),
    ("What is a REST API?",
     "A REST API is an architectural style for networked applications where clients interact with servers using standard HTTP methods (GET, POST, PUT, DELETE) to exchange data, typically in JSON format."),
    ("What is a GPU?",
     "A GPU (Graphics Processing Unit) is a processor originally designed for rendering graphics but now widely used for parallel computing tasks like training AI models."),
    ("What is blockchain?",
     "Blockchain is a distributed ledger technology that records transactions across many computers so that the record cannot be altered retroactively, used in cryptocurrencies and other applications."),
    ("What is Docker?",
     "Docker is a platform for developing, shipping, and running applications in containers — lightweight, portable environments that include all dependencies needed to run the software."),
    ("What is Linux?",
     "Linux is an open-source Unix-like operating system kernel first released by Linus Torvalds in 1991, widely used in servers, embedded systems, and as the basis for Android."),
    # History
    ("In what year did World War II end?",
     "World War II ended in 1945, with Germany surrendering in May and Japan in September."),
    ("Who was the first President of the United States?",
     "George Washington was the first President of the United States, serving from 1789 to 1797."),
    ("When did the French Revolution begin?",
     "The French Revolution began in 1789."),
    ("What was the Renaissance?",
     "The Renaissance was a cultural and intellectual movement that began in Italy in the 14th century and spread across Europe, marking the transition from the Middle Ages to modernity."),
    ("Who was Napoleon Bonaparte?",
     "Napoleon Bonaparte was a French military leader and emperor who conquered much of Europe in the early 19th century before his defeat and exile."),
    ("What was the Cold War?",
     "The Cold War was a period of geopolitical tension between the United States and the Soviet Union lasting from the end of World War II (1947) until the dissolution of the USSR in 1991."),
    ("Who invented the printing press?",
     "Johannes Gutenberg invented the movable-type printing press around 1440, revolutionizing the spread of information in Europe."),
    ("What was the Industrial Revolution?",
     "The Industrial Revolution was the transition from agrarian economies to manufacturing-based ones, beginning in Britain in the late 18th century and transforming global society and production."),
    # Geography
    ("What is the longest river in the world?",
     "The Nile River in Africa is traditionally considered the longest river in the world, stretching approximately 6,650 kilometers."),
    ("What is the largest ocean?",
     "The Pacific Ocean is the largest ocean, covering more than 165 million square kilometers."),
    ("What is the highest mountain in the world?",
     "Mount Everest, located in the Himalayas on the border of Nepal and Tibet, is the highest mountain at 8,848.86 meters above sea level."),
    ("What is the smallest country in the world?",
     "Vatican City is the smallest country in the world, covering just 0.44 square kilometers within Rome, Italy."),
    ("What is the Amazon rainforest?",
     "The Amazon rainforest is the world's largest tropical rainforest, covering over 5.5 million square kilometers across nine South American countries."),
    ("What is the Sahara Desert?",
     "The Sahara is the world's largest hot desert, covering about 9.2 million square kilometers across North Africa."),
    # Biology
    ("What is a cell?",
     "A cell is the basic structural and functional unit of all living organisms, capable of performing all life processes independently."),
    ("What is evolution?",
     "Evolution is the process of gradual change in inherited characteristics of populations over successive generations, driven by natural selection, mutation, and genetic drift."),
    ("What is an ecosystem?",
     "An ecosystem is a community of living organisms interacting with each other and their physical environment, such as a forest, ocean, or desert."),
    ("What is the function of the heart?",
     "The heart is a muscular organ that pumps blood throughout the body via the circulatory system, delivering oxygen and nutrients to tissues and removing waste products."),
    ("What is a virus?",
     "A virus is a microscopic infectious agent that replicates only inside living cells of an organism, consisting of genetic material (DNA or RNA) enclosed in a protein coat."),
    ("What is the difference between bacteria and viruses?",
     "Bacteria are single-celled living organisms that can reproduce independently, while viruses are non-living particles that require a host cell to replicate. Bacteria can be treated with antibiotics; viruses cannot."),
    ("What is metabolism?",
     "Metabolism is the set of chemical reactions in an organism that maintain life, including processes that convert food to energy and build or break down molecules."),
    # Philosophy & Economics
    ("What is philosophy?",
     "Philosophy is the study of fundamental questions about existence, knowledge, values, reason, mind, and language, using critical and systematic reasoning."),
    ("What is ethics?",
     "Ethics is a branch of philosophy concerned with questions of right and wrong, moral principles, and how individuals should act toward one another."),
    ("What is GDP?",
     "GDP (Gross Domestic Product) is the total monetary value of all goods and services produced within a country in a specific time period, used as a measure of economic output."),
    ("What is inflation?",
     "Inflation is the rate at which the general level of prices for goods and services rises over time, reducing the purchasing power of currency."),
    ("What is supply and demand?",
     "Supply and demand is a fundamental economic model describing how the price and quantity of goods are determined by the relationship between availability (supply) and consumer desire (demand)."),
    ("What is cryptocurrency?",
     "Cryptocurrency is a digital or virtual currency secured by cryptography, operating on decentralized networks (usually blockchain), with Bitcoin being the most well-known example."),
    # Language
    ("What language has the most native speakers?",
     "Mandarin Chinese has the most native speakers, with over one billion people speaking it as their first language."),
    ("What is a synonym?",
     "A synonym is a word that has the same or nearly the same meaning as another word. For example, 'happy' and 'joyful' are synonyms."),
    ("How many languages are spoken in the world?",
     "There are approximately 7,000 languages spoken in the world today, though many are endangered."),
]


def make_sample(q, a):
    return {
        "conversation": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": q},
            {"role": "assistant", "content": a},
        ]
    }


data = []

# Dynamic: math
for _ in range(300):
    a, b = random.randint(1, 100), random.randint(1, 100)
    op = random.choice(["+", "-", "*"])
    c = a + b if op == "+" else a - b if op == "-" else a * b
    verb = "sum" if op == "+" else "difference" if op == "-" else "product"
    data.append(make_sample(f"What is {a} {op} {b}?", f"The {verb} of {a} and {b} is {c}."))

# Dynamic: square roots
for _ in range(100):
    sq, sqr = random.choice(squares)
    data.append(make_sample(f"What is the square root of {sq}?", f"The square root of {sq} is {sqr}."))

# Dynamic: prime numbers
for _ in range(100):
    n = random.randint(2, 50)
    ans = f"Yes, {n} is a prime number." if n in primes else f"No, {n} is not a prime number."
    data.append(make_sample(f"Is {n} a prime number?", ans))

# Dynamic: chemical symbols
for _ in range(100):
    el, sym = random.choice(elements)
    data.append(make_sample(f"What is the chemical symbol for {el}?", f"The chemical symbol for {el} is {sym}."))

# Dynamic: planets
for _ in range(80):
    epi, planet = random.choice(planets)
    data.append(make_sample(f"What planet is known as the {epi} planet?", f"The {epi} planet is {planet}."))

# Dynamic: capitals
for _ in range(200):
    country, capital = random.choice(capitals)
    data.append(make_sample(f"What is the capital of {country}?", f"The capital of {country} is {capital}."))

# Static Q&A repeated with shuffling to reach 2000
static_pool = static_qa * ((2000 // len(static_qa)) + 2)
random.shuffle(static_pool)
remaining = 2000 - len(data)
for q, a in static_pool[:remaining]:
    data.append(make_sample(q, a))

random.shuffle(data)
data = data[:2000]

output_path = "test_dataset.json"
with open(output_path, "w") as f:
    json.dump(data, f, indent=2)

print(f"Generated {len(data)} samples -> {output_path}")
