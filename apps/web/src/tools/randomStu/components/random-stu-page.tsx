"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import styles from "./random-stu-page.module.css";
import { recognizeRosterImage } from "../client/recognize-roster";
import {
  EMPTY_RANDOM_STU_DATA,
  loadRandomStuData,
  saveRandomStuData,
} from "../lib/storage";
import type { Classroom, RandomStuData, Student } from "../lib/types";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

function createId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

function emptyStudent(index: number): Student {
  return { id: createId(), number: String(index + 1), name: "", enabled: true };
}

function randomIndex(length: number): number {
  const range = 0x1_0000_0000;
  const limit = range - (range % length);
  const values = new Uint32Array(1);
  do globalThis.crypto.getRandomValues(values);
  while (values[0] >= limit);
  return values[0] % length;
}

export function RandomStuPage() {
  const [data, setData] = useState<RandomStuData>(EMPTY_RANDOM_STU_DATA);
  const [draftStudents, setDraftStudents] = useState<Student[]>([]);
  const [className, setClassName] = useState("");
  const [hydrated, setHydrated] = useState(false);
  const [notice, setNotice] = useState("");
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [isRecognizing, setIsRecognizing] = useState(false);
  const drawTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);

  const activeClassroom = data.classrooms.find(
    (classroom) => classroom.id === data.activeClassroomId,
  );

  useEffect(() => {
    const saved = loadRandomStuData();
    setData(saved);
    const active = saved.classrooms.find(
      (classroom) => classroom.id === saved.activeClassroomId,
    );
    setDraftStudents(active?.students ?? []);
    setHydrated(true);
  }, []);

  useEffect(() => {
    return () => {
      if (drawTimerRef.current) clearTimeout(drawTimerRef.current);
    };
  }, []);

  function persist(next: RandomStuData) {
    setData(next);
    saveRandomStuData(next);
  }

  function cancelDrawing() {
    if (drawTimerRef.current) clearTimeout(drawTimerRef.current);
    drawTimerRef.current = null;
    setIsDrawing(false);
  }

  function createClassroom() {
    const name = className.trim();
    if (!name) {
      setNotice("请先填写班级名称");
      return;
    }

    cancelDrawing();
    const now = new Date().toISOString();
    const classroom: Classroom = {
      id: createId(),
      name,
      students: [],
      locked: false,
      createdAt: now,
      updatedAt: now,
    };
    const next = {
      version: 1 as const,
      classrooms: [...data.classrooms, classroom],
      activeClassroomId: classroom.id,
    };
    persist(next);
    setDraftStudents([]);
    setClassName("");
    setSelectedStudent(null);
    setNotice("班级已创建");
  }

  function selectClassroom(classroom: Classroom) {
    cancelDrawing();
    persist({ ...data, activeClassroomId: classroom.id });
    setDraftStudents(classroom.students);
    setSelectedStudent(null);
    setNotice("");
  }

  function updateStudent(id: string, patch: Partial<Student>) {
    if (activeClassroom?.locked) return;
    setDraftStudents((students) =>
      students.map((student) =>
        student.id === id ? { ...student, ...patch } : student,
      ),
    );
    setNotice("");
  }

  function addStudent() {
    if (activeClassroom?.locked) return;
    setDraftStudents((students) => [...students, emptyStudent(students.length)]);
    setNotice("");
  }

  function removeStudent(id: string) {
    if (activeClassroom?.locked) return;
    setDraftStudents((students) => students.filter((student) => student.id !== id));
    setNotice("");
  }

  function saveRoster() {
    if (!activeClassroom || activeClassroom.locked) return;
    const students = draftStudents
      .map((student) => ({
        ...student,
        number: student.number.trim(),
        name: student.name.trim(),
      }))
      .filter((student) => student.name);
    const now = new Date().toISOString();
    const next = {
      ...data,
      classrooms: data.classrooms.map((classroom) =>
        classroom.id === activeClassroom.id
          ? { ...classroom, students, updatedAt: now }
          : classroom,
      ),
    };
    persist(next);
    setDraftStudents(students);
    setNotice(`已保存 ${students.length} 名学生，本地数据不会自动过期`);
  }

  function clearRoster() {
    if (!activeClassroom || activeClassroom.locked) return;
    cancelDrawing();
    const now = new Date().toISOString();
    const next = {
      ...data,
      classrooms: data.classrooms.map((classroom) =>
        classroom.id === activeClassroom.id
          ? { ...classroom, students: [], updatedAt: now }
          : classroom,
      ),
    };
    persist(next);
    setDraftStudents([]);
    setSelectedStudent(null);
    setNotice("当前班级名单已清除");
  }

  function deleteClassroom() {
    if (!activeClassroom || activeClassroom.locked) return;
    const confirmed = window.confirm(
      `确定删除“${activeClassroom.name}”吗？该班级的学生名单也会被永久删除。`,
    );
    if (!confirmed) return;
    cancelDrawing();

    const classrooms = data.classrooms.filter(
      (classroom) => classroom.id !== activeClassroom.id,
    );
    const nextActiveClassroom = classrooms[0] ?? null;
    persist({
      ...data,
      classrooms,
      activeClassroomId: nextActiveClassroom?.id ?? null,
    });
    setDraftStudents(nextActiveClassroom?.students ?? []);
    setSelectedStudent(null);
    setNotice(
      nextActiveClassroom
        ? `“${activeClassroom.name}”已删除`
        : "班级已删除，请创建一个新班级",
    );
  }

  function toggleClassroomLock() {
    if (!activeClassroom) return;
    const locked = !activeClassroom.locked;
    const students = locked
      ? draftStudents
          .map((student) => ({
            ...student,
            number: student.number.trim(),
            name: student.name.trim(),
          }))
          .filter((student) => student.name)
      : activeClassroom.students;
    const now = new Date().toISOString();
    const next = {
      ...data,
      classrooms: data.classrooms.map((classroom) =>
        classroom.id === activeClassroom.id
          ? { ...classroom, students, locked, updatedAt: now }
          : classroom,
      ),
    };
    persist(next);
    setDraftStudents(students);
    setNotice(locked ? "名单已保存并锁定" : "名单已解锁，可以继续修改");
  }

  async function recognizeImage(file: File) {
    if (!activeClassroom || activeClassroom.locked || isRecognizing) return;
    if (file.size > 12 * 1024 * 1024) {
      setNotice("图片不能超过 12 MB");
      return;
    }

    setIsRecognizing(true);
    setNotice("DeepSeek 正在识别图片中的学生名单...");
    try {
      const recognized = await recognizeRosterImage(file);
      setDraftStudents((students) => {
        const identities = new Set(
          students.map((student) => `${student.number.trim()}\u0000${student.name.trim()}`),
        );
        const additions = recognized
          .filter((student) => student.name.trim())
          .filter((student) => {
            const identity = `${student.number.trim()}\u0000${student.name.trim()}`;
            if (identities.has(identity)) return false;
            identities.add(identity);
            return true;
          })
          .map<Student>((student) => ({
            id: createId(),
            number: student.number.trim(),
            name: student.name.trim(),
            enabled: true,
          }));
        return [...students, ...additions];
      });
      setNotice(`识别出 ${recognized.length} 名学生，请检查并点击“保存名单”`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "图片识别失败，请稍后重试");
    } finally {
      setIsRecognizing(false);
      if (uploadInputRef.current) uploadInputRef.current.value = "";
    }
  }

  function drawStudent() {
    if (isDrawing) return;
    const candidates = activeClassroom?.students.filter(
      (student) => student.enabled && student.name,
    );
    if (!candidates?.length) {
      setNotice("请先保存至少一名参与抽取的学生");
      return;
    }
    const winner = candidates[randomIndex(candidates.length)];
    setIsDrawing(true);
    setNotice("");
    drawTimerRef.current = setTimeout(() => {
      setSelectedStudent(winner);
      setIsDrawing(false);
      drawTimerRef.current = null;
    }, 1000);
  }

  if (!hydrated) return <main className={styles.loading}>正在读取本地名单...</main>;

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>课堂小工具 · RANDOM STU</p>
          <h1>随机点名</h1>
          <p className={styles.subtitle}>把机会交给随机，也把注意力留在课堂。</p>
        </div>
        <div className={styles.storageBadge}>仅保存在当前浏览器</div>
      </header>

      {data.classrooms.length > 0 && (
        <nav className={styles.classTabs} aria-label="班级列表">
          {data.classrooms.map((classroom) => (
            <button
              className={classroom.id === data.activeClassroomId ? styles.activeTab : styles.tab}
              key={classroom.id}
              onClick={() => selectClassroom(classroom)}
              type="button"
            >
              {classroom.name}
              <span>{classroom.students.length} 人</span>
            </button>
          ))}
          <button className={styles.addClassTab} onClick={() => setData({ ...data, activeClassroomId: null })} type="button">
            新建班级
          </button>
        </nav>
      )}

      {!activeClassroom ? (
        <section className={styles.emptyCard}>
          <div className={styles.emptyMark}>01</div>
          <h2>先创建一个班级</h2>
          <p>班级和保存后的名单会一直留在本机浏览器中，除非你主动清除浏览器数据。</p>
          <div className={styles.createRow}>
            <input
              aria-label="班级名称"
              onChange={(event) => setClassName(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && createClassroom()}
              placeholder="例如：高二（5）班"
              value={className}
            />
            <button onClick={createClassroom} type="button">创建班级</button>
          </div>
        </section>
      ) : (
        <div className={styles.workspace}>
          <section className={styles.drawCard}>
            <div className={styles.cardHeading}>
              <div>
                <span>当前班级</span>
                <h2>{activeClassroom.name}</h2>
              </div>
              <strong>{activeClassroom.students.length} 名学生</strong>
            </div>
            <div className={styles.resultStage} aria-live="polite">
              <span className={styles.resultNumber}>{isDrawing ? "DRAWING" : (selectedStudent?.number || "READY")}</span>
              <strong>{isDrawing ? "猜猜会是谁？" : (selectedStudent?.name || "等待随机抽取")}</strong>
              <p>{isDrawing ? "小狗正在努力抽取中..." : (selectedStudent ? "本次抽取结果" : "保存名单后即可开始")}</p>
            </div>
            <div className={styles.drawButtonWrap}>
              {isDrawing && (
                <Image
                  alt=""
                  aria-hidden="true"
                  className={styles.dog}
                  height={58}
                  src={`${basePath}/randomStu/dog-loading.gif`}
                  unoptimized
                  width={58}
                />
              )}
              <button
                className={`${styles.drawButton} ${isDrawing ? styles.drawingButton : ""}`}
                disabled={isDrawing}
                onClick={drawStudent}
                type="button"
              >
                <span>{isDrawing ? "正在抽取" : "随机抽取"}</span>
              </button>
            </div>
          </section>

          <section className={styles.rosterCard}>
            <div className={styles.rosterHeader}>
              <div>
                <span>名单管理</span>
                <h2>确认后保存到本机</h2>
              </div>
              <div className={styles.rosterActions}>
                <button
                  aria-pressed={activeClassroom.locked}
                  className={activeClassroom.locked ? styles.unlockButton : styles.lockButton}
                  onClick={toggleClassroomLock}
                  type="button"
                >
                  {activeClassroom.locked ? "解锁" : "锁定"}
                </button>
                <button className={styles.clearButton} disabled={activeClassroom.locked} onClick={clearRoster} type="button">清除名单</button>
                <button className={styles.deleteClassButton} disabled={activeClassroom.locked} onClick={deleteClassroom} type="button">删除班级</button>
              </div>
            </div>

            <div className={styles.importPanel}>
              <div>
                <strong>图片识别名单</strong>
                <p>上传清晰的名单表格，AI 会提取序号和姓名，识别结果可继续修改。</p>
              </div>
              <input
                ref={uploadInputRef}
                accept="image/png,image/jpeg,image/webp,image/gif"
                className={styles.fileInput}
                disabled={activeClassroom.locked || isRecognizing}
                onChange={(event) => {
                  const file = event.currentTarget.files?.[0];
                  if (file) void recognizeImage(file);
                }}
                type="file"
              />
              <button
                className={styles.uploadButton}
                disabled={activeClassroom.locked || isRecognizing}
                onClick={() => uploadInputRef.current?.click()}
                type="button"
              >
                {isRecognizing ? (
                  <><span aria-hidden="true" className={styles.recognitionSpinner} />正在识别</>
                ) : "上传图片识别"}
              </button>
            </div>

            <div className={styles.columnLabels}>
              <span>参与</span><span>序号</span><span>学生姓名</span><span>操作</span>
            </div>
            <div className={styles.studentList}>
              {draftStudents.map((student) => (
                <div className={styles.studentRow} key={student.id}>
                  <input
                    aria-label={`${student.name || "学生"}是否参与抽取`}
                    checked={student.enabled}
                    disabled={activeClassroom.locked}
                    onChange={(event) => updateStudent(student.id, { enabled: event.target.checked })}
                    type="checkbox"
                  />
                  <input
                    aria-label="学生序号"
                    disabled={activeClassroom.locked}
                    onChange={(event) => updateStudent(student.id, { number: event.target.value })}
                    placeholder="序号"
                    value={student.number}
                  />
                  <input
                    aria-label="学生姓名"
                    disabled={activeClassroom.locked}
                    onChange={(event) => updateStudent(student.id, { name: event.target.value })}
                    placeholder="输入姓名"
                    value={student.name}
                  />
                  <button disabled={activeClassroom.locked} onClick={() => removeStudent(student.id)} type="button">删除</button>
                </div>
              ))}
              {draftStudents.length === 0 && <p className={styles.noStudents}>暂无学生，先手动添加；识别功能接入后也会显示在这里。</p>}
            </div>

            <button className={styles.addStudentButton} disabled={activeClassroom.locked} onClick={addStudent} type="button">+ 添加学生</button>
            <div className={styles.saveBar}>
              <p>{notice || (activeClassroom.locked ? "名单已锁定，解锁后才可以修改。" : "修改不会自动保存，请确认名单后点击保存。")}</p>
              <button disabled={activeClassroom.locked} onClick={saveRoster} type="button">保存名单</button>
            </div>
          </section>
        </div>
      )}
      {!activeClassroom && notice && <p className={styles.notice}>{notice}</p>}
    </main>
  );
}
