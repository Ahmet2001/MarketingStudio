import {
  CalendarClock,
  CheckCircle2,
  Clock3,
  MoreHorizontal,
  Play,
  Plus,
  X,
} from "lucide-react";
import type { ScheduledProject } from "../types";

interface SchedulerPageProps {
  schedules: ScheduledProject[];
  loading: boolean;
  onCreate: () => void;
  onCancel: (scheduleId: string) => Promise<void>;
  onRunNow: (scheduleId: string) => Promise<void>;
}

function formatScheduleDate(value: string): {
  day: string;
  date: string;
  time: string;
} {
  const date = new Date(value);
  return {
    day: date.toLocaleDateString([], { weekday: "short" }).toUpperCase(),
    date: date.toLocaleDateString([], { month: "short", day: "numeric" }),
    time: date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  };
}

export function SchedulerPage({
  schedules,
  loading,
  onCreate,
  onCancel,
  onRunNow,
}: SchedulerPageProps) {
  const activeCount = schedules.filter(
    (schedule) => schedule.status === "Scheduled",
  ).length;

  return (
    <section className="scheduler-page">
      <div className="page-heading-row">
        <div>
          <span className="page-kicker">Automation</span>
          <h1>Video scheduler</h1>
          <p>Queue ideas now and let Storyforge start them at the right time.</p>
        </div>
        <button className="primary-button" type="button" onClick={onCreate}>
          <Plus size={17} />
          Schedule video
        </button>
      </div>

      <div className="scheduler-summary">
        <div className="scheduler-summary-icon">
          <CalendarClock size={23} />
        </div>
        <div>
          <strong>{activeCount} upcoming</strong>
          <span>Times are displayed in your local timezone.</span>
        </div>
        <div className="scheduler-live">
          <i />
          Scheduler online
        </div>
      </div>

      {loading ? (
        <div className="empty-state">
          <Clock3 className="spin" size={28} />
          <h2>Loading schedules</h2>
        </div>
      ) : schedules.length ? (
        <div className="schedule-list">
          {schedules.map((schedule) => {
            const date = formatScheduleDate(schedule.runAt);
            return (
              <article className="schedule-card" key={schedule.id}>
                <div className="schedule-date">
                  <span>{date.day}</span>
                  <strong>{date.date}</strong>
                  <small>{date.time}</small>
                </div>
                <div className="schedule-info">
                  <span>{schedule.projectMode}</span>
                  <h2>{schedule.projectTitle}</h2>
                  <small>
                    {schedule.error ??
                      `${schedule.timezone.replace("_", " ")} · Generation`}
                  </small>
                </div>
                <span
                  className={`schedule-status schedule-${schedule.status.toLowerCase()}`}
                >
                  {schedule.status === "Triggered" ? (
                    <CheckCircle2 size={13} />
                  ) : (
                    <Clock3 size={13} />
                  )}
                  {schedule.status}
                </span>
                <div className="schedule-actions">
                  {schedule.status === "Scheduled" ? (
                    <>
                      <button
                        type="button"
                        onClick={() => void onRunNow(schedule.id)}
                        title="Run now"
                        aria-label={`Run ${schedule.projectTitle} now`}
                      >
                        <Play size={16} />
                      </button>
                      <button
                        type="button"
                        onClick={() => void onCancel(schedule.id)}
                        title="Cancel schedule"
                        aria-label={`Cancel ${schedule.projectTitle}`}
                      >
                        <X size={17} />
                      </button>
                    </>
                  ) : (
                    <button type="button" aria-label="More schedule options">
                      <MoreHorizontal size={18} />
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="empty-state">
          <CalendarClock size={30} />
          <h2>Nothing scheduled yet</h2>
          <p>Choose a video format and select “Schedule for later.”</p>
          <button className="secondary-button" type="button" onClick={onCreate}>
            <Plus size={16} />
            Schedule first video
          </button>
        </div>
      )}
    </section>
  );
}
