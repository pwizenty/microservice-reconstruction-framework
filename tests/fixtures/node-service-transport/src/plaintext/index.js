const grpc = require('@grpc/grpc-js')
const nconf = require('nconf')
const stompit = require('stompit')

function consume() {
  const mq_config = nconf.get('activemq')
  const connectOptions = {
    host: mq_config.host,
    port: mq_config.port,
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
  const server = new grpc.Server()
  server.addService(service, implementation)
  server.bindAsync(
    `${grpc_config.host}:${grpc_config.port}`,
    grpc.ServerCredentials.createInsecure(),
    () => server.start()
  )
}

module.exports = { consume, serve }
