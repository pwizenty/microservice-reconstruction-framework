const fs = require('fs')
const grpc = require('@grpc/grpc-js')
const nconf = require('nconf')
const stompit = require('stompit')

function material() {
  const tls_config = nconf.get('tls')
  return {
    key: fs.readFileSync(tls_config.key),
    cert: fs.readFileSync(tls_config.cert),
    ca: fs.readFileSync(tls_config.ca),
  }
}

function consume() {
  const mq_config = nconf.get('activemq')
  const tls = material()
  const connectOptions = {
    host: mq_config.host,
    port: mq_config.port,
    ssl: true,
    key: tls.key,
    cert: tls.cert,
    ca: tls.ca,
    connectHeaders: {
      login: mq_config.username,
      passcode: mq_config.password,
    },
  }
  const connectFailover = new stompit.ConnectFailover([connectOptions])
  return new stompit.ChannelFactory(connectFailover)
}

function serve(service, implementation) {
  const grpc_config = nconf.get('grpc')
  const tls = material()
  const server = new grpc.Server()
  server.addService(service, implementation)
  // The third argument makes the server require a client certificate and
  // verify it, which is what mutual TLS adds over plain TLS.
  const credentials = grpc.ServerCredentials.createSsl(
    tls.ca,
    [{ private_key: tls.key, cert_chain: tls.cert }],
    true
  )
  server.bindAsync(
    `${grpc_config.host}:${grpc_config.port}`,
    credentials,
    () => server.start()
  )
}

module.exports = { consume, serve }
