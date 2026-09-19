import type { Classroom, RandomStuData, Student } from "./types";

type StoredClassroom = Omit<Classroom, "locked"> & { locked?: boolean };

const STORAGE_KEY = "tiny.tools.randomStu.v1";

export const EMPTY_RANDOM_STU_DATA: RandomStuData = {
  version: 1,
  classrooms: [],
  activeClassroomId: null,
};

function isStudent(value: unknown): value is Student {
  if (!value || typeof value !== "object") return false;
  const student = value as Partial<Student>;
  return (
    typeof student.id === "string" &&
    typeof student.number === "string" &&
    typeof student.name === "string" &&
    typeof student.enabled === "boolean"
  );
}

function isClassroom(value: unknown): value is StoredClassroom {
  if (!value || typeof value !== "object") return false;
  const classroom = value as Partial<Classroom>;
  return (
    typeof classroom.id === "string" &&
    typeof classroom.name === "string" &&
    Array.isArray(classroom.students) &&
    classroom.students.every(isStudent) &&
    (typeof classroom.locked === "boolean" || classroom.locked === undefined) &&
    typeof classroom.createdAt === "string" &&
    typeof classroom.updatedAt === "string"
  );
}

export function loadRandomStuData(): RandomStuData {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return EMPTY_RANDOM_STU_DATA;

    const parsed = JSON.parse(raw) as Partial<RandomStuData>;
    if (parsed.version !== 1 || !Array.isArray(parsed.classrooms)) {
      return EMPTY_RANDOM_STU_DATA;
    }

    const classrooms = parsed.classrooms
      .filter(isClassroom)
      .map((classroom) => ({ ...classroom, locked: classroom.locked === true }));
    const activeClassroomId = classrooms.some(
      (classroom) => classroom.id === parsed.activeClassroomId,
    )
      ? (parsed.activeClassroomId ?? null)
      : (classrooms[0]?.id ?? null);

    return { version: 1, classrooms, activeClassroomId };
  } catch {
    return EMPTY_RANDOM_STU_DATA;
  }
}

export function saveRandomStuData(data: RandomStuData): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}
