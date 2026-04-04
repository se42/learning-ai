# Foundational Designs

Our team runs a mature Ruby on Rails web service with something like 50 API
endpoints (with multiple RESTful HTTP actions each) and an extensive and
complex data model. We have decided to pursue a service-oriented architecture
to adding AI capabilities to our service for three primary reasons:

1. New project serves as an AI focus hub--good for the team to minimize context
   switching, establish reusable patterns, more easily cooperate across team functions, etc.
2. Allows the use of Python and thus access to industry-leading tools and frameworks
3. Keeping the LLMs outside the API boundary offers substantial authorization safety

We will eventually be able to run fully agentic workloads in this new service
and expose it directly to users so they can take full advantage of the intelligence
we build and run on our compute, but we need to find some simpler pathways to
get started while we work through some key engineering problems, such as how to
manage authentication and authorization across the existing Rails service and the
new intelligence service.

What I am thinking will offer two good pathways for our team to get started are:

1. Distributable MCP server and corresponding skills, e.g. a Docker image our users
   can run in their IDE (Cursor, Windsurf, etc.) and simply provide their existing
   Rails API token. This would let them use their local compute and LLM connections
   to drive the MCP server, and it would be authorized to make existing API calls
   on their behalf. We could start by releasing a "naive" MCP server that more or
   less just mirrors our API, but then begin working on more mature "curated" tools
   as our users report what they need. Our Rails app does publish an OpenAPI spec
   (actually three, there's a v1, v2, and v3 json file), so and easy way to start
   is probably the FastAPI/FastMCP integration that allows the generation of an
   MCP server from an OpenAPI specification. But we also already have some ideas
   for some more "curated" tools and corresponding skills.
2. An internal-only API microservice that our Rails app can call over HTTP for simple
   AI capabilities. Things like basic research tasks that can be fully executed
   using only the data POSTed to the intelligence service, and that do not yet
   require any form of memory or agent checkpointing. Just dead simple features
   that give the existing Rails application a sense of "intelligence" when it
   is valuable. This service oriented approach may seem like overkill for this
   use case, but we will be building the service towards more complex use cases
   like user-specific and user-authorized agentic workflows with write operations,
   and the long term vision is to run all of our intelligence here as an architectural
   preference, so these basic features are just the first steps.

What I want you to do is to build some simple demonstration resources that will
help me learn the fundamental concepts I need to know to lead my team through these
first steps. These are the first questions that come to mind:

1. Are these solid first steps that will be achievable with minimal ops/infra work?
   Or am I overlooking anything?
2. Are these generally valuable patterns to have in our toolkit? "Value" ultimately
   comes down to users and their needs, but are these generally popular patterns
   that people are having success with in 2026?
3. Our API has a fair few endpoints: what tools are available in the OpenAPI spec
   to perhaps tag endpoints that would turn into MCP tool groups? This might let
   our users tune the MCP server a bit to suit their needs, perhaps with CLI flags
   on startup.
4. What do I need to understand about the interplay of a distributable MCP server
   and corresponding SKILLs (Anthropic SKILL.md spec), and how can I explain this
   in simple terms to my teammates? How this distributable image approach compare
   and contrast to a hosted/remote MCP server that we will probably build later?
5. For the internal-only intelligence microservice, the initial features need to
   be very basic and not require any form of authorization. Things like the Rails
   service basically just proxying LLM chat calls through the intelligencee service
   API, or the Rails app using the intelligence service to search the docs site
   to offer suggestions to users opening support cases. What are some common
   patterns being employed in 2026 that would fit into this phase of our buildout?
   And how can I communicate this situation to my teammates, that we are limited
   in our capabilities now as we learn and as we properly build out our authorization
   framework, but we will graduate into more complex capabilities over time so it's
   important to commit to the service-oriented approach even when the first few
   steps seem like architectural overkill / YAGNI? I suspect adding even a modicum
   of complexity will very quickly justify our decision--what are the obvious next
   steps that would add the complexities that justify our choice of a Python-based
   microservice for all of our intelligence capabilities?

I want you to thoroughly review and research what I've described, and then build out
some FOCUSED and TARGETED demo resources to help me learn the most important concepts
I need to know to build this out. I didn't tell you all about the details of our service,
so just focus on FUNDAMENTALS. I'd like to see a few demo implementations, e.g. a
basic MCP server from a mock OpenAPI spec and some skills to go with it, and a dummy
microservice geared towards servicing very basic LLM requests on behalf of a Rails app.
I'd also like you to write some clear and concise instructional text explaining the
basic principles of the first steps I've layed out, again staying ruthlessly focused
on the FUNDAMENTALS that my teammates and I need to understand to be successful with
our first steps.
