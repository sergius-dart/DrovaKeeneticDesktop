#!/bin/sh


RECORDINGS_DIR="/var/recordings"

DAYS_OLD=30

# Количество дней для хранения логов (60 дней)
LOG_RETENTION=60

LOG_FILE="${RECORDINGS_DIR}/cleanup.log"

MAX_LOG_SIZE_MB=10

if [ -f "$LOG_FILE" ]; then
    # Проверяем размер лога в MB
    LOG_SIZE=$(du -m "$LOG_FILE" | cut -f1)
    if [ "$LOG_SIZE" -gt "$MAX_LOG_SIZE_MB" ]; then
        echo "Log file too large ($LOG_SIZE MB), rotating..." >> $LOG_FILE
        # Создаём бэкап с датой
        mv "$LOG_FILE" "$LOG_FILE.$(date +%Y%m%d_%H%M%S).bak"
        # Создаём новый пустой лог
        touch "$LOG_FILE"
        echo "=== New log file created at $(date) ===" >> $LOG_FILE
    fi
fi

# 4. Удаляем старые бэкапы логов (старше LOG_RETENTION дней)
echo "Removing log backups older than $LOG_RETENTION days..." >> $LOG_FILE
find "$RECORDINGS_DIR" -type f -name "cleanup.log.*.bak" -mtime +$LOG_RETENTION -delete -print >> $LOG_FILE 2>&1

echo "=== Cleanup started at $(date) ===" >> $LOG_FILE

# Delete all record older then DAYS_OLD days
find "$RECORDINGS_DIR" -type f -name "*.flv" -mtime +$DAYS_OLD -delete -print >> $LOG_FILE 2>&1

# Статистика
RECORDED_COUNT=$(find "$RECORDINGS_DIR" -type f -name "*.flv" | wc -l)
RECORDED_SIZE=$(du -sh "$RECORDINGS_DIR" | cut -f1)

echo "Cleanup finished at $(date)" >> $LOG_FILE
echo "Total recordings: $RECORDED_COUNT, Total size: $RECORDED_SIZE" >> $LOG_FILE
echo "----------------------------------------" >> $LOG_FILE
