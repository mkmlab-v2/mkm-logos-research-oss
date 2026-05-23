import { smartfarmCopy } from "@/content/smartfarmCopy";

const f = smartfarmCopy.flow;

/** CSS-only field → cloud → MKM diagram (no vendor trademarked artwork). */
export function SystemFlowDiagram() {
  return (
    <figure className="sf-system-flow">
      <figcaption className="sf-sr-only">
        토양 센서와 밸브가 게이트웨이로 연결되고 LTE로 MKM 서버와 앱에 데이터가 전달되는 구조
      </figcaption>

      <div className="sf-system-field">
        <p className="sf-system-zone-label">{f.fieldLabel}</p>
        <div className="sf-system-field-grid">
          <div className="sf-system-tanks">
            <span className="sf-system-chip sf-system-chip--water">{f.nodes.tanks}</span>
            <span className="sf-system-chip sf-system-chip--valve">{f.nodes.valves}</span>
          </div>
          <span className="sf-system-pipe-line" aria-hidden="true" />
          <span className="sf-system-chip sf-system-chip--drip">{f.nodes.drip}</span>
          <div className="sf-system-sensors">
            <span className="sf-system-sensor-dot" aria-hidden="true" />
            <span className="sf-system-sensor-dot" aria-hidden="true" />
            <span className="sf-system-sensor-dot" aria-hidden="true" />
            <span className="sf-system-chip">{f.nodes.sensors}</span>
          </div>
          <div className="sf-system-gateway">
            <span className="sf-system-lora">LoRa</span>
            <span className="sf-system-gw-box">{f.nodes.gateway}</span>
          </div>
        </div>
      </div>

      <div className="sf-system-uplink" aria-hidden="true">
        <span className="sf-system-uplink-line" />
        <span className="sf-system-uplink-label">{f.cloudLabel}</span>
        <span className="sf-system-uplink-line" />
      </div>

      <div className="sf-system-mkm">
        <p className="sf-system-zone-label">{f.serverLabel}</p>
        <div className="sf-system-mkm-row">
          <span className="sf-system-mkm-box">{f.nodes.server}</span>
          <span className="sf-system-mkm-arrow" aria-hidden="true">
            →
          </span>
          <span className="sf-system-mkm-box sf-system-mkm-box--app">{f.nodes.app}</span>
        </div>
      </div>

      <p className="sf-system-protocol">{f.protocolNote}</p>
      <p className="sf-system-caption">{f.caption}</p>
    </figure>
  );
}
