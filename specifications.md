# Формальные спецификации системы

## **0. Спецификация 0. Проверка корректности региона памяти задачи**

### **Предусловия**
- Задача требует память объёма `S`:  
  **P1:** `task.mem_request = S`
- Максимально доступная память системы:  
  **P2:** `0 ≤ S ≤ MAX_MEMORY`
- Задача имеет корректно заданные границы региона:  
  **P3:** `task.addr_start ≥ 0`
- Конечный адрес корректен:  
  **P4:** `task.addr_end = task.addr_start + S`
- Конечный адрес лежит в допустимых границах:  
  **P5:** `task.addr_end ≤ MAX_MEMORY`

### **Постусловия**
- Регион памяти задачи считается валидным:  
  **Q1:** `validate_task(task) = True`

### **Инварианты**
- Любой регион задачи должен иметь положительный размер:  
  **I1:** `task.addr_end > task.addr_start`
- Никакой регион не может выходить за пределы памяти:  
  **I2:** `0 ≤ task.addr_start < task.addr_end ≤ MAX_MEMORY`

### **Логика первого порядка**
`∀task : validate_task(task) ↔ (0 ≤ addr_start ∧ addr_end ≤ MAX_MEMORY ∧ addr_end > addr_start)`

### **Темпоральная логика**
- Любой регион, поступающий в аллокатор, сначала проходит проверку:  
  `@ (new_task → # validate_task(task))`

---

## **1. Спецификация 1. Выделение памяти под задачу (Memory Allocate)**

### **Предусловия**
- `task.mem_request = S`
- `∃ region ⊆ M : size(region) ≥ S`

### **Постусловия**
- `task.mem_region = region`
- `allocated(region) = True`

### **Инварианты**
- `t1 ≠ t2 → t1.mem_region ≠ t2.mem_region`
- `¬∃ r1,r2 : allocated(r1) ∧ allocated(r2) ∧ overlap(r1,r2)`

### **Логика первого порядка**
`∀task : mem_request(task) → ∃region : alloc(task, region)`

### **Темпоральная логика**
`@ (P2 → # allocated(region))`

---

## **2. Спецификация 2. Планирование задачи TPC (добавление в очередь CU)**

### **Предусловия**
- `CU.status = WAIT`
- `|CU.queue| < CU.max_size`

### **Постусловия**
- `task ∈ CU.queue`

### **Инварианты**
- `order(CU.queue)` — FIFO  
- Нет дубликатов задач: `¬duplication(task, queue)`

### **Логика первого порядка**
`∀task : status(CU)=WAIT → enqueue(CU, task)`

### **Темпоральная логика**
`@ (CU.status = WAIT → # (task ∈ CU.queue))`

---

## **3. Спецификация 3. Исполнитель (Executor) должен завершить задачу**

### **Предусловия**
- `assigned(task, exec)`
- `(exec.state = WAIT) ∧ (exec._active_task = None)`

### **Постусловия**
- `task.is_completed = True`
- `(exec.state = WAIT) ∧ (exec._active_task = None)`

### **Инварианты**
- Исполнитель обрабатывает ≤ 1 задачи
- Выполненная задача всегда имеет флаг `completed`

### **Логика первого порядка**
`∀task : assigned(task, exec) → executes(exec, task)`

### **Темпоральная логика**
`@ (assigned(task, exec) → # task.is_completed)`

---

## **4. Спецификация 4. Передача данных: TPC_CU должна доставить задачу Executor'у**

### **Предусловия**
- `CU.queue ≠ ∅`
- `exec.status = WAIT`

### **Постусловия**
- `task ∉ CU.queue`
- `exec.status = VPU | exec.status = ME | exec.status = FE`

### **Инварианты**
- FIFO-порядок очереди сохраняется

### **Логика первого порядка**
`∀task ∈ CU.queue : deliver(task, exec)`

### **Темпоральная логика**
`@ (task ∈ CU.queue → # exec.status = VPU | exec.status = ME | exec.status = FE)`

---

## **5. Спецификация 5. Аллокация памяти и правила доступа при пересечениях**

### **Предусловия**
- `allocated(task.mem_region)`
- `addr ∈ task.mem_region`

### **Постусловия**
- `read(addr)` возвращает корректные данные
- Запись возможна только в эксклюзивные регионы

### **Инварианты**
- Если регионы перекрываются → только чтение:  
  `overlap(r1,r2) → (access(r1)=READ ∧ access(r2)=READ)`
- Исключение гонок записи:  
  `¬∃ t1,t2 : write(t1,addr) ∧ write(t2,addr)`

### **Логика первого порядка**
`∀addr : valid_addr(addr, task) → access_allowed(task, addr)`

### **Темпоральная логика**
`@ ¬WRITE_conflict`  
`@ (addr ∈ shared → READ_allowed(addr))`

---
